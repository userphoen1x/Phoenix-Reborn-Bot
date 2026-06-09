import os
import random
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dishka.integrations.aiogram import inject, FromDishka

from services.casino_service import CasinoService
from core.exceptions import UserNotRegisteredError, NotEnoughMoneyError
from core.constants import SAPER_DIFFS, DELAYS
from core.lexicon import LEXICON
from tg_bot.keyboards.inline import CasinoCb, BjCb, SaperSetupCb, SaperCb, kb_casino_main, kb_casino_bet, \
    kb_saper_setup_bet, kb_saper_setup_diff, kb_saper_game
from core.garbage_collector import schedule_delete

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}),
                      lambda msg: str(msg.chat.id) != os.getenv("ADMIN_CHAT_ID"))

LAST_GAME_MSGS = {}


def is_cmd(text: str, cmds: list) -> bool:
    if not text: return False
    t = text.lower().strip()
    return any(t == c or t.startswith(c + " ") for c in cmds)


async def cleanup_old_game(bot: Bot, chat_id: int, user_id: int):
    if user_id in LAST_GAME_MSGS:
        for mid in LAST_GAME_MSGS[user_id]:
            try:
                await bot.delete_message(chat_id, mid)
            except:
                pass
        del LAST_GAME_MSGS[user_id]


def get_deck():
    suits = ['♠️', '♥️', '♦️', '♣️']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    random.shuffle(deck)
    return deck


def calc_hand(hand):
    val = 0
    aces = 0
    for card in hand:
        r = card[:-2]
        if r in ['J', 'Q', 'K']:
            val += 10
        elif r == 'A':
            val += 11
            aces += 1
        else:
            val += int(r)
    while val > 21 and aces > 0:
        val -= 10
        aces -= 1
    return val


@router.message(lambda msg: is_cmd(msg.text, ["казик", "казино", "игра", "игры", "casino", "games"]))
@inject
async def cmd_casino_main(message: Message, casino_service: FromDishka[CasinoService]):
    user_id = message.from_user.id
    try:
        balance = await casino_service.get_balance(user_id)
        sent_msg = await message.answer(LEXICON["casino_welcome"].format(balance=balance),
                                        reply_markup=kb_casino_main(balance), parse_mode="HTML")
        await cleanup_old_game(message.bot, message.chat.id, user_id)
        LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
        schedule_delete(sent_msg, DELAYS["default"])
    except UserNotRegisteredError as e:
        sent = await message.answer(str(e))
        schedule_delete(sent, DELAYS["default"])


@router.message(
    lambda msg: is_cmd(msg.text, ["слоты", "слот", "кости", "кубик", "дартс", "боулинг", "футбол", "баскет"]))
@inject
async def cmd_direct_games(message: Message, casino_service: FromDishka[CasinoService]):
    parts = message.text.lower().split()
    cmd = parts[0]
    game = "slot" if any(x in cmd for x in ["слот"]) else "dice" if any(
        x in cmd for x in ["кост", "кубик"]) else "darts" if any(x in cmd for x in ["дартс"]) else "bowl" if any(
        x in cmd for x in ["боул"]) else "fball" if any(x in cmd for x in ["футб", "ногом"]) else "bball"
    user_id = message.from_user.id
    try:
        balance = await casino_service.get_balance(user_id)
        bet_str = next((p for p in parts[1:] if p.isdigit() or p in ["all", "все", "всё"]), None)
        if not bet_str:
            game_names = {"slot": "🎰 Слоты", "dice": "🎲 Кости", "darts": "🎯 Дартс", "bowl": "🎳 Боулинг",
                          "fball": "⚽️ Футбол", "bball": "🏀 Баскетбол"}
            sent_msg = await message.answer(LEXICON["casino_bet_prompt"].format(game_name=game_names[game]),
                                            reply_markup=kb_casino_bet(game), parse_mode="HTML")
            await cleanup_old_game(message.bot, message.chat.id, user_id)
            LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
            schedule_delete(sent_msg, DELAYS["default"])
            return
        bet = balance if bet_str in ["all", "все", "всё"] else int(bet_str)
        if bet < 10: return await message.answer(LEXICON["casino_min_bet"])
        guess = None
        if game == "dice":
            for p in parts[1:]:
                if p.isdigit() and int(p) in [1, 2, 3, 4, 5, 6] and p != bet_str:
                    guess = int(p)
                    break
            if not guess:
                kb_dice_guess = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="1️⃣",
                                          callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_1").pack()),
                     InlineKeyboardButton(text="2️⃣",
                                          callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_2").pack()),
                     InlineKeyboardButton(text="3️⃣",
                                          callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_3").pack())],
                    [InlineKeyboardButton(text="4️⃣",
                                          callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_4").pack()),
                     InlineKeyboardButton(text="5️⃣",
                                          callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_5").pack()),
                     InlineKeyboardButton(text="6️⃣",
                                          callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_6").pack())],
                    [InlineKeyboardButton(text="❌ Отмена", callback_data=CasinoCb(act="menu", game="none").pack())]
                ])
                sent_msg = await message.answer(LEXICON["casino_dice_guess"].format(bet=bet),
                                                reply_markup=kb_dice_guess, parse_mode="HTML")
                await cleanup_old_game(message.bot, message.chat.id, user_id)
                LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
                schedule_delete(sent_msg, DELAYS["default"])
                return
        emoji_map = {"slot": "🎰", "dice": "🎲", "darts": "🎯", "bowl": "🎳", "fball": "⚽", "bball": "🏀"}
        dice_msg = await message.answer_dice(emoji=emoji_map[game])
        import asyncio
        await asyncio.sleep(
            DELAYS["casino_slot"] if game in ["slot", "bowl", "fball", "bball"] else DELAYS["casino_dice"])
        msg_result, win_amount = await casino_service.play_emoji_game(user_id=user_id, game=game, bet=bet,
                                                                      dice_value=dice_msg.dice.value, guess=guess)
        res_text = LEXICON["casino_result"].format(emoji=emoji_map[game], dice_value=dice_msg.dice.value,
                                                   msg_result=msg_result, win_amount=win_amount)
        retry_val = str(bet) if game != "dice" else f"{bet}_{guess}"
        kb_retry = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить партию",
                                                                               callback_data=CasinoCb(act="play",
                                                                                                      game=game,
                                                                                                      val=retry_val).pack())]])
        res_msg = await message.answer(res_text, reply_markup=kb_retry, parse_mode="HTML")
        LAST_GAME_MSGS[user_id] = [dice_msg.message_id, res_msg.message_id]
        schedule_delete(dice_msg, DELAYS["default"])
        schedule_delete(res_msg, DELAYS["default"])
    except (UserNotRegisteredError, NotEnoughMoneyError) as e:
        await message.answer(str(e))


@router.callback_query(CasinoCb.filter())
@inject
async def cb_casino_handler(callback: CallbackQuery, callback_data: CasinoCb,
                            casino_service: FromDishka[CasinoService]):
    user_id = callback.from_user.id
    act = callback_data.act
    game = callback_data.game
    val = callback_data.val
    if act == "close": return await callback.message.delete()
    if act == "menu":
        await cleanup_old_game(callback.bot, callback.message.chat.id, user_id)
        try:
            await callback.message.delete()
        except:
            pass
        try:
            balance = await casino_service.get_balance(user_id)
            sent_msg = await callback.message.answer(LEXICON["casino_welcome"].format(balance=balance),
                                                     reply_markup=kb_casino_main(balance), parse_mode="HTML")
            LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
            schedule_delete(sent_msg, DELAYS["default"])
        except UserNotRegisteredError:
            pass
        return
    if act == "saper_route": return await callback.message.edit_text(LEXICON["saper_bet_prompt"],
                                                                     reply_markup=kb_saper_setup_bet(),
                                                                     parse_mode="HTML")
    if act == "bet":
        game_names = {"bj": "🃏 Блэкджек", "slot": "🎰 Слоты", "dice": "🎲 Кости", "darts": "🎯 Дартс", "bowl": "🎳 Боулинг",
                      "fball": "⚽️ Футбол", "bball": "🏀 Баскетбол"}
        return await callback.message.edit_text(LEXICON["casino_bet_prompt"].format(game_name=game_names[game]),
                                                reply_markup=kb_casino_bet(game), parse_mode="HTML")
    if act == "play" and game == "dice" and "_" not in val:
        try:
            balance = await casino_service.get_balance(user_id)
            bet = balance if val == "all" else int(val)
            if balance < bet: return await callback.answer(LEXICON["casino_no_money"], show_alert=True)
            kb_dice_guess = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="1️⃣",
                                      callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_1").pack()),
                 InlineKeyboardButton(text="2️⃣",
                                      callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_2").pack()),
                 InlineKeyboardButton(text="3️⃣",
                                      callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_3").pack())],
                [InlineKeyboardButton(text="4️⃣",
                                      callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_4").pack()),
                 InlineKeyboardButton(text="5️⃣",
                                      callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_5").pack()),
                 InlineKeyboardButton(text="6️⃣",
                                      callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_6").pack())],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data=CasinoCb(act="bet", game="dice").pack())]
            ])
            await callback.message.edit_text(LEXICON["casino_dice_guess"].format(bet=bet), reply_markup=kb_dice_guess,
                                             parse_mode="HTML")
        except UserNotRegisteredError:
            pass
        return
    if act == "play":
        try:
            balance = await casino_service.get_balance(user_id)
            if game == "dice":
                bet, guess = int(val.split("_")[0]), int(val.split("_")[1])
            else:
                bet, guess = (balance if val == "all" else int(val)), None
            if balance < bet: return await callback.answer(LEXICON["casino_no_money"], show_alert=True)
            if game == "bj": return await start_blackjack(callback, user_id, bet, casino_service)

            await cleanup_old_game(callback.bot, callback.message.chat.id, user_id)
            try:
                await callback.message.delete()
            except:
                pass

            emoji_map = {"slot": "🎰", "dice": "🎲", "darts": "🎯", "bowl": "🎳", "fball": "⚽", "bball": "🏀"}
            dice_msg = await callback.message.answer_dice(emoji=emoji_map[game])
            import asyncio
            await asyncio.sleep(
                DELAYS["casino_slot"] if game in ["slot", "bowl", "fball", "bball"] else DELAYS["casino_dice"])
            msg_result, win_amount = await casino_service.play_emoji_game(user_id=user_id, game=game, bet=bet,
                                                                          dice_value=dice_msg.dice.value, guess=guess)
            res_text = LEXICON["casino_result"].format(emoji=emoji_map[game], dice_value=dice_msg.dice.value,
                                                       msg_result=msg_result, win_amount=win_amount)
            retry_val = str(bet) if game != "dice" else f"{bet}_{guess}"
            kb_retry = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить",
                                                                                   callback_data=CasinoCb(act="play",
                                                                                                          game=game,
                                                                                                          val=retry_val).pack())],
                                                             [InlineKeyboardButton(text="⬅️ Меню игр",
                                                                                   callback_data=CasinoCb(act="menu",
                                                                                                          game="none").pack())]])
            res_msg = await callback.message.answer(res_text, reply_markup=kb_retry, parse_mode="HTML")

            LAST_GAME_MSGS[user_id] = [dice_msg.message_id, res_msg.message_id]
            schedule_delete(dice_msg, DELAYS["default"])
            schedule_delete(res_msg, DELAYS["default"])
        except (UserNotRegisteredError, NotEnoughMoneyError) as e:
            await callback.answer(str(e), show_alert=True)


async def start_blackjack(callback: CallbackQuery, user_id: int, bet: int, casino_service: CasinoService):
    bot = callback.bot
    chat_id = callback.message.chat.id
    await cleanup_old_game(bot, chat_id, user_id)
    try:
        await callback.message.delete()
    except:
        pass

    await casino_service.charge_bet(user_id, bet)
    deck = get_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    pval = calc_hand(player_hand)
    p_hand_str = ", ".join(player_hand)
    d_card = dealer_hand[0]

    text = LEXICON["bj_state"].format(bet=bet, d_card=d_card, p_hand=p_hand_str, pval=pval)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👇 Ещё карту", callback_data=BjCb(act="hit").pack()),
         InlineKeyboardButton(text="✋ Хватит", callback_data=BjCb(act="stand").pack())]])

    sent_msg = await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
    LAST_GAME_MSGS[user_id] = [sent_msg.message_id]

    state = {"bet": bet, "deck": deck, "player_hand": player_hand, "dealer_hand": dealer_hand,
             "msg_id": sent_msg.message_id}
    await casino_service.save_active_game(user_id, "bj", state)

    if pval == 21: await finish_blackjack(callback, user_id, "bj", casino_service)


async def render_blackjack(message: Message, user_id: int, casino_service: CasinoService):
    game_data = await casino_service.get_active_game(user_id)
    if not game_data or game_data["game_type"] != "bj": return
    game = game_data["state"]

    p_hand = ", ".join(game["player_hand"])
    d_card = game["dealer_hand"][0]
    pval = calc_hand(game["player_hand"])
    text = LEXICON["bj_state"].format(bet=game['bet'], d_card=d_card, p_hand=p_hand, pval=pval)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👇 Ещё карту", callback_data=BjCb(act="hit").pack()),
         InlineKeyboardButton(text="✋ Хватит", callback_data=BjCb(act="stand").pack())]])
    await message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(BjCb.filter())
@inject
async def cb_bj_handler(callback: CallbackQuery, callback_data: BjCb, casino_service: FromDishka[CasinoService]):
    user_id = callback.from_user.id
    game_data = await casino_service.get_active_game(user_id)
    if not game_data or game_data["game_type"] != "bj": return await callback.answer(LEXICON["casino_game_over"],
                                                                                     show_alert=True)

    game = game_data["state"]
    act = callback_data.act

    if act == "hit":
        game["player_hand"].append(game["deck"].pop())
        pval = calc_hand(game["player_hand"])
        await casino_service.save_active_game(user_id, "bj", game)

        if pval > 21:
            await finish_blackjack(callback, user_id, "bust", casino_service)
        elif pval == 21:
            await finish_blackjack(callback, user_id, "stand", casino_service)
        else:
            await render_blackjack(callback.message, user_id, casino_service)
    elif act == "stand":
        await finish_blackjack(callback, user_id, "stand", casino_service)


async def finish_blackjack(callback: CallbackQuery, user_id: int, reason: str, casino_service: CasinoService):
    bot = callback.bot
    chat_id = callback.message.chat.id
    game_data = await casino_service.get_active_game(user_id)
    if not game_data or game_data["game_type"] != "bj": return
    game = game_data["state"]

    await casino_service.delete_active_game(user_id)

    bet = game["bet"]
    p_hand = game["player_hand"]
    d_hand = game["dealer_hand"]
    deck = game["deck"]
    msg_id = game.get("msg_id")
    pval = calc_hand(p_hand)

    if reason == "bust":
        mult, res_msg = 0.0, "💥 Перебор! Ты проиграл."
    elif reason == "bj":
        mult, res_msg = 2.5, "🎉 БЛЭКДЖЕК с раздачи! Чистая победа! (x2.5)"
    else:
        dval = calc_hand(d_hand)
        while dval < 17:
            d_hand.append(deck.pop())
            dval = calc_hand(d_hand)
        if dval > 21:
            mult, res_msg = 2.0, "🔥 Дилер перебрал! Ты выиграл! (x2)"
        elif pval > dval:
            mult, res_msg = 2.0, "🏆 Ты победил дилера! (x2)"
        elif pval == dval:
            mult, res_msg = 1.0, "🤝 Ничья! Ставка возвращена."
        else:
            mult, res_msg = 0.0, "😔 Дилер оказался сильнее. Ставка сгорела."

    win_amount = int(bet * mult)
    await casino_service.credit_win(user_id, win_amount)

    p_str = ", ".join(p_hand)
    d_str = ", ".join(d_hand)
    dval = calc_hand(d_hand)
    text = LEXICON["bj_result"].format(d_hand=d_str, dval=dval, p_hand=p_str, pval=pval, res_msg=res_msg,
                                       win_amount=win_amount)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Повторить", callback_data=CasinoCb(act="play", game="bj", val=str(bet)).pack())],
        [InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())]])
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb, parse_mode="HTML")
    except:
        pass


@router.message(lambda msg: is_cmd(msg.text, ["блекджек", "блэкджек", "21", "очко"]))
@inject
async def cmd_bj_direct(message: Message, casino_service: FromDishka[CasinoService]):
    user_id = message.from_user.id
    parts = message.text.lower().split()
    try:
        balance = await casino_service.get_balance(user_id)
        if len(parts) > 1 and (parts[1].isdigit() or parts[1] == "all"):
            val = parts[1]
            bet = balance if val == "all" else int(val)
            if bet < 10: return await message.answer(LEXICON["casino_min_bet"])
            if balance < bet: return await message.answer(LEXICON["casino_no_money"])

            class FakeCb:
                def __init__(self, msg):
                    self.message = msg
                    self.from_user = msg.from_user
                    self.bot = msg.bot

            await start_blackjack(FakeCb(message), user_id, bet, casino_service)
        else:
            sent_msg = await message.answer(LEXICON["casino_bet_prompt"].format(game_name="🃏 <b>БЛЭКДЖЕК</b>"),
                                            reply_markup=kb_casino_bet("bj"), parse_mode="HTML")
            await cleanup_old_game(message.bot, message.chat.id, user_id)
            LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
            schedule_delete(sent_msg, DELAYS["default"])
    except UserNotRegisteredError as e:
        sent = await message.answer(str(e))
        schedule_delete(sent, DELAYS["default"])


@router.message(lambda msg: is_cmd(msg.text, ["сапер", "saper", "сапёр"]))
@inject
async def cmd_saper(message: Message, casino_service: FromDishka[CasinoService]):
    user_id = message.from_user.id
    parts = message.text.lower().split()[1:]
    bet_str = None
    diff = None
    diff_synonyms = {"easy": ["легкий", "изи", "easy", "легко", "1"],
                     "medium": ["средний", "нормальный", "med", "medium", "норм", "2"],
                     "hard": ["трудный", "сложный", "hard", "хард", "3"]}
    for part in parts:
        if part.isdigit() or part in ["all", "все", "всё"]:
            bet_str = "all" if part in ["all", "все", "всё"] else part
        else:
            for d_key, syns in diff_synonyms.items():
                if part in syns:
                    diff = d_key
                    break
    await cleanup_old_game(message.bot, message.chat.id, user_id)
    if not bet_str:
        sent_msg = await message.answer(LEXICON["saper_bet_prompt"], reply_markup=kb_saper_setup_bet(),
                                        parse_mode="HTML")
        LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
        schedule_delete(sent_msg, DELAYS["default"])
        return
    if not diff:
        sent_msg = await message.answer(LEXICON["saper_diff_prompt"].format(bet=bet_str),
                                        reply_markup=kb_saper_setup_diff(bet_str), parse_mode="HTML")
        LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
        schedule_delete(sent_msg, DELAYS["default"])
        return
    await start_saper_game(message.chat.id, user_id, message.from_user.full_name, bet_str, diff, casino_service,
                           bot_msg=message)


async def start_saper_game(chat_id: int, user_id: int, user_name: str, bet_str: str, diff: str,
                           casino_service: CasinoService, bot_msg=None):
    bot = bot_msg.bot if hasattr(bot_msg, 'bot') else getattr(bot_msg.message, 'bot', None)
    await cleanup_old_game(bot, chat_id, user_id)

    async def send_error(txt):
        if isinstance(bot_msg, Message):
            msg = await bot_msg.answer(txt)
            schedule_delete(msg, DELAYS["default"])
        elif isinstance(bot_msg, CallbackQuery):
            await bot_msg.message.edit_text(txt)

    try:
        balance = await casino_service.get_balance(user_id)
        bet = balance if bet_str == "all" else int(bet_str)
        if bet < 10: return await send_error(LEXICON["saper_min_bet"])

        await casino_service.charge_bet(user_id, bet)
        mines_count = SAPER_DIFFS[diff]["mines"]
        grid = [0] * 25
        mine_indices = random.sample(range(25), mines_count)
        for i in mine_indices: grid[i] = 1

        state = {"chat_id": chat_id, "name": user_name, "bet": bet, "diff": diff, "grid": grid, "clicked": [],
                 "mult": 1.0}
        await casino_service.save_active_game(user_id, "saper", state)

        text = LEXICON["saper_start"].format(name=user_name, diff_name=SAPER_DIFFS[diff]['name'], bet=bet)
        if isinstance(bot_msg, CallbackQuery):
            try:
                await bot_msg.message.delete()
            except:
                pass

        sent_msg = await bot.send_message(chat_id, text, reply_markup=kb_saper_game(state), parse_mode="HTML")
        LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
        schedule_delete(sent_msg, DELAYS["default"])
    except (UserNotRegisteredError, NotEnoughMoneyError) as e:
        await send_error(str(e))


@router.callback_query(SaperSetupCb.filter())
@inject
async def cb_saper_setup(callback: CallbackQuery, callback_data: SaperSetupCb,
                         casino_service: FromDishka[CasinoService]):
    user_id = callback.from_user.id
    act = callback_data.act
    val = callback_data.val
    if act == "cancel": return await callback.message.delete()
    if act == "bet":
        await callback.message.edit_text(LEXICON["saper_diff_prompt"].format(bet=val),
                                         reply_markup=kb_saper_setup_diff(val), parse_mode="HTML")
    elif act.startswith("start_"):
        bet_str = act.split("_")[1]
        await start_saper_game(callback.message.chat.id, user_id, callback.from_user.full_name, bet_str, val,
                               casino_service, bot_msg=callback)


@router.callback_query(SaperCb.filter())
@inject
async def cb_saper_play(callback: CallbackQuery, callback_data: SaperCb, casino_service: FromDishka[CasinoService]):
    user_id = callback.from_user.id
    game_data = await casino_service.get_active_game(user_id)
    if callback_data.act == "ignore": return await callback.answer()
    if not game_data or game_data["game_type"] != "saper": return await callback.answer(LEXICON["saper_not_your_game"],
                                                                                        show_alert=True)

    game = game_data["state"]
    if game["chat_id"] != callback.message.chat.id: return await callback.answer(LEXICON["saper_chat_error"],
                                                                                 show_alert=True)

    act = callback_data.act
    idx = callback_data.idx

    if act == "cashout":
        win_amount = int(game["bet"] * game["mult"])
        await casino_service.credit_win(user_id, win_amount)
        text = LEXICON["saper_cashout"].format(name=game['name'], diff_name=SAPER_DIFFS[game['diff']]['name'],
                                               win_amount=win_amount, mult=round(game['mult'], 1))
        kb = kb_saper_game(game, game_over=True)
        kb.inline_keyboard.append([InlineKeyboardButton(text="🔄 Повторить партию",
                                                        callback_data=SaperSetupCb(act=f"start_{game['bet']}",
                                                                                   val=game['diff']).pack())])
        kb.inline_keyboard.append(
            [InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await casino_service.delete_active_game(user_id)
        return

    if act == "click":
        if idx in game["clicked"]: return await callback.answer(LEXICON["saper_already_open"], show_alert=False)
        if game["grid"][idx] == 1:
            game["clicked"].append(idx)
            text = LEXICON["saper_boom"].format(name=game['name'], bet=game['bet'])
            kb = kb_saper_game(game, game_over=True)
            kb.inline_keyboard.append([InlineKeyboardButton(text="🔄 Повторить партию",
                                                            callback_data=SaperSetupCb(act=f"start_{game['bet']}",
                                                                                       val=game['diff']).pack())])
            kb.inline_keyboard.append(
                [InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())])
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            await casino_service.delete_active_game(user_id)
            return

        game["clicked"].append(idx)
        game["mult"] += SAPER_DIFFS[game["diff"]]["mult_step"]
        safe_total = SAPER_DIFFS[game["diff"]]["safe"]

        if len(game["clicked"]) == safe_total:
            win_amount = int(game["bet"] * game["mult"])
            await casino_service.credit_win(user_id, win_amount)
            text = LEXICON["saper_win"].format(name=game['name'], win_amount=win_amount, mult=round(game['mult'], 1))
            kb = kb_saper_game(game, game_over=True)
            kb.inline_keyboard.append([InlineKeyboardButton(text="🔄 Повторить партию",
                                                            callback_data=SaperSetupCb(act=f"start_{game['bet']}",
                                                                                       val=game['diff']).pack())])
            kb.inline_keyboard.append(
                [InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())])
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            await casino_service.delete_active_game(user_id)
            return

        await casino_service.save_active_game(user_id, "saper", game)
        current_win = int(game["bet"] * game["mult"])
        text = LEXICON["saper_continue"].format(name=game['name'], diff_name=SAPER_DIFFS[game['diff']]['name'],
                                                bet=game['bet'], current_win=current_win, mult=round(game['mult'], 2))
        try:
            await callback.message.edit_text(text, reply_markup=kb_saper_game(game), parse_mode="HTML")
        except:
            pass