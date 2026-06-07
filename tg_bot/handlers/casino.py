import asyncio
import os
import random
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.casino_service import CasinoService
from core.exceptions import UserNotRegisteredError, NotEnoughMoneyError
from core.constants import SAPER_DIFFS
from tg_bot.keyboards.inline import CasinoCb, BjCb, SaperSetupCb, SaperCb, kb_casino_main, kb_casino_bet, kb_saper_setup_bet, kb_saper_setup_diff, kb_saper_game

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), lambda msg: str(msg.chat.id) != os.getenv("ADMIN_CHAT_ID"))

LAST_GAME_MSGS = {}
BJ_GAMES = {}
SAPER_GAMES = {}

def is_cmd(text: str, cmds: list) -> bool:
    if not text: return False
    t = text.lower().strip()
    return any(t == c or t.startswith(c + " ") for c in cmds)

async def delete_later(message: Message, delay: int = 10800):
    await asyncio.sleep(delay)
    try: await message.delete()
    except: pass

async def cleanup_old_game(bot: Bot, chat_id: int, user_id: int):
    if user_id in LAST_GAME_MSGS:
        for mid in LAST_GAME_MSGS[user_id]:
            try: await bot.delete_message(chat_id, mid)
            except: pass
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
        if r in ['J', 'Q', 'K']: val += 10
        elif r == 'A':
            val += 11
            aces += 1
        else: val += int(r)
    while val > 21 and aces > 0:
        val -= 10
        aces -= 1
    return val

@router.message(lambda msg: is_cmd(msg.text, ["казик", "казино", "игра", "игры", "casino", "games"]))
async def cmd_casino_main(message: Message, casino_service: CasinoService):
    user_id = message.from_user.id
    try:
        balance = await casino_service.get_balance(user_id)
        sent_msg = await message.answer(f"🎰 <b>КАЗИНО PHOENIX</b> 🎰\n\n💰 Твой баланс: <b>{balance}</b> ₣\n\nВыбери игру, чтобы испытать удачу:", reply_markup=kb_casino_main(balance), parse_mode="HTML")
        await cleanup_old_game(message.bot, message.chat.id, user_id)
        LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
        asyncio.create_task(delete_later(sent_msg))
    except UserNotRegisteredError as e:
        sent = await message.answer(str(e))
        asyncio.create_task(delete_later(sent, 60))

@router.message(lambda msg: is_cmd(msg.text, ["слоты", "слот", "кости", "кубик", "дартс", "боулинг", "футбол", "баскет"]))
async def cmd_direct_games(message: Message, casino_service: CasinoService):
    parts = message.text.lower().split()
    cmd = parts[0]
    game = "slot" if any(x in cmd for x in ["слот"]) else "dice" if any(x in cmd for x in ["кост", "кубик"]) else "darts" if any(x in cmd for x in ["дартс"]) else "bowl" if any(x in cmd for x in ["боул"]) else "fball" if any(x in cmd for x in ["футб", "ногом"]) else "bball"
    user_id = message.from_user.id
    try:
        balance = await casino_service.get_balance(user_id)
        bet_str = next((p for p in parts[1:] if p.isdigit() or p in ["all", "все", "всё"]), None)
        if not bet_str:
            game_names = {"slot": "🎰 Слоты", "dice": "🎲 Кости", "darts": "🎯 Дартс", "bowl": "🎳 Боулинг", "fball": "⚽️ Футбол", "bball": "🏀 Баскетбол"}
            sent_msg = await message.answer(f"{game_names[game]}\n\nВыберите размер ставки:", reply_markup=kb_casino_bet(game), parse_mode="HTML")
            await cleanup_old_game(message.bot, message.chat.id, user_id)
            LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
            asyncio.create_task(delete_later(sent_msg))
            return
        bet = balance if bet_str in ["all", "все", "всё"] else int(bet_str)
        if bet < 10: return await message.answer("❌ Минимальная ставка 10 ₣!")
        guess = None
        if game == "dice":
            for p in parts[1:]:
                if p.isdigit() and int(p) in [1, 2, 3, 4, 5, 6] and p != bet_str:
                    guess = int(p)
                    break
            if not guess:
                kb_dice_guess = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="1️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_1").pack()), InlineKeyboardButton(text="2️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_2").pack()), InlineKeyboardButton(text="3️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_3").pack())],
                    [InlineKeyboardButton(text="4️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_4").pack()), InlineKeyboardButton(text="5️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_5").pack()), InlineKeyboardButton(text="6️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_6").pack())],
                    [InlineKeyboardButton(text="❌ Отмена", callback_data=CasinoCb(act="menu", game="none").pack())]
                ])
                sent_msg = await message.answer(f"🎲 Ставка: <b>{bet} ₣</b>\n\nНа какое число ставишь?", reply_markup=kb_dice_guess, parse_mode="HTML")
                await cleanup_old_game(message.bot, message.chat.id, user_id)
                LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
                asyncio.create_task(delete_later(sent_msg))
                return
        emoji_map = {"slot": "🎰", "dice": "🎲", "darts": "🎯", "bowl": "🎳", "fball": "⚽", "bball": "🏀"}
        dice_msg = await message.answer_dice(emoji=emoji_map[game])
        await asyncio.sleep(4.0 if game in ["slot", "bowl", "fball", "bball"] else 3.0)
        msg_result, win_amount = await casino_service.play_emoji_game(user_id=user_id, game=game, bet=bet, dice_value=dice_msg.dice.value, guess=guess)
        res_text = f"{emoji_map[game]} <b>РЕЗУЛЬТАТ: {dice_msg.dice.value}</b>\n\n{msg_result}\n💸 Выигрыш: <b>{win_amount} ₣</b>"
        kb_retry = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить партию", callback_data=CasinoCb(act="play", game=game, val=str(bet)).pack())]])
        res_msg = await message.answer(res_text, reply_markup=kb_retry, parse_mode="HTML")
        LAST_GAME_MSGS[user_id] = [dice_msg.message_id, res_msg.message_id]
        asyncio.create_task(delete_later(dice_msg))
        asyncio.create_task(delete_later(res_msg))
    except (UserNotRegisteredError, NotEnoughMoneyError) as e:
        await message.answer(str(e))

@router.callback_query(CasinoCb.filter())
async def cb_casino_handler(callback: CallbackQuery, callback_data: CasinoCb, casino_service: CasinoService):
    user_id = callback.from_user.id
    act = callback_data.act
    game = callback_data.game
    val = callback_data.val
    if act == "close":
        await callback.message.delete()
        return
    if act == "menu":
        await cleanup_old_game(callback.bot, callback.message.chat.id, user_id)
        try: await callback.message.delete()
        except: pass
        try:
            balance = await casino_service.get_balance(user_id)
            sent_msg = await callback.message.answer(f"🎰 <b>КАЗИНО PHOENIX</b> 🎰\n\n💰 Твой баланс: <b>{balance}</b> ₣\n\nВыбери игру:", reply_markup=kb_casino_main(balance), parse_mode="HTML")
            LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
            asyncio.create_task(delete_later(sent_msg))
        except UserNotRegisteredError: pass
        return
    if act == "saper_route":
        await callback.message.edit_text("💣 <b>САПЕР</b>\n\nВыберите сумму ставки (мин. 10 ₣):", reply_markup=kb_saper_setup_bet(), parse_mode="HTML")
        return
    if act == "bet":
        game_names = {"bj": "🃏 Блэкджек", "slot": "🎰 Слоты", "dice": "🎲 Кости", "darts": "🎯 Дартс", "bowl": "🎳 Боулинг", "fball": "⚽️ Футбол", "bball": "🏀 Баскетбол"}
        await callback.message.edit_text(f"{game_names[game]}\n\nВыберите размер ставки:", reply_markup=kb_casino_bet(game), parse_mode="HTML")
        return
    if act == "play" and game == "dice" and "_" not in val:
        try:
            balance = await casino_service.get_balance(user_id)
            bet = balance if val == "all" else int(val)
            if balance < bet: return await callback.answer("Недостаточно средств!", show_alert=True)
            kb_dice_guess = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="1️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_1").pack()), InlineKeyboardButton(text="2️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_2").pack()), InlineKeyboardButton(text="3️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_3").pack())],
                [InlineKeyboardButton(text="4️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_4").pack()), InlineKeyboardButton(text="5️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_5").pack()), InlineKeyboardButton(text="6️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_6").pack())],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data=CasinoCb(act="bet", game="dice").pack())]
            ])
            await callback.message.edit_text(f"🎲 Ставка: <b>{bet} ₣</b>\n\nНа какое число ставишь?", reply_markup=kb_dice_guess, parse_mode="HTML")
        except UserNotRegisteredError: pass
        return
    if act == "play":
        try:
            balance = await casino_service.get_balance(user_id)
            if game == "dice":
                bet = int(val.split("_")[0])
                guess = int(val.split("_")[1])
            else:
                bet = balance if val == "all" else int(val)
                guess = None
            if balance < bet: return await callback.answer("Недостаточно средств!", show_alert=True)
            if game == "bj": return await start_blackjack(callback, user_id, bet, casino_service)
            await cleanup_old_game(callback.bot, callback.message.chat.id, user_id)
            try: await callback.message.delete()
            except: pass
            emoji_map = {"slot": "🎰", "dice": "🎲", "darts": "🎯", "bowl": "🎳", "fball": "⚽", "bball": "🏀"}
            dice_msg = await callback.message.answer_dice(emoji=emoji_map[game])
            await asyncio.sleep(4.0 if game in ["slot", "bowl", "fball", "bball"] else 3.0)
            msg_result, win_amount = await casino_service.play_emoji_game(user_id=user_id, game=game, bet=bet, dice_value=dice_msg.dice.value, guess=guess)
            res_text = f"{emoji_map[game]} <b>РЕЗУЛЬТАТ: {dice_msg.dice.value}</b>\n\n{msg_result}\n💸 Выигрыш: <b>{win_amount} ₣</b>"
            retry_val = str(bet) if game != "dice" else f"{bet}_{guess}"
            kb_retry = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить", callback_data=CasinoCb(act="play", game=game, val=retry_val).pack())], [InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())]])
            res_msg = await callback.message.answer(res_text, reply_markup=kb_retry, parse_mode="HTML")
            LAST_GAME_MSGS[user_id] = [dice_msg.message_id, res_msg.message_id]
            asyncio.create_task(delete_later(dice_msg))
            asyncio.create_task(delete_later(res_msg))
        except (UserNotRegisteredError, NotEnoughMoneyError) as e:
            await callback.answer(str(e), show_alert=True)

async def start_blackjack(callback: CallbackQuery, user_id: int, bet: int, casino_service: CasinoService):
    bot = callback.bot
    chat_id = callback.message.chat.id
    await cleanup_old_game(bot, chat_id, user_id)
    try: await callback.message.delete()
    except: pass
    await casino_service.charge_bet(user_id, bet)
    deck = get_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    BJ_GAMES[user_id] = {"bet": bet, "deck": deck, "player_hand": player_hand, "dealer_hand": dealer_hand}
    pval = calc_hand(player_hand)
    p_hand = ", ".join(player_hand)
    d_card = dealer_hand[0]
    text = f"🃏 <b>БЛЭКДЖЕК</b>\n\n💸 Ставка: <b>{bet} ₣</b>\n\n🏦 Дилер: {d_card}, 🂠 (?)\n👤 Ты: {p_hand} <b>({pval})</b>\n\nТвой ход:"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👇 Ещё карту", callback_data=BjCb(act="hit").pack()), InlineKeyboardButton(text="✋ Хватит", callback_data=BjCb(act="stand").pack())]])
    sent_msg = await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
    LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
    BJ_GAMES[user_id]["msg_id"] = sent_msg.message_id
    if pval == 21: await finish_blackjack(callback, user_id, "bj", casino_service)

async def render_blackjack(message: Message, user_id: int):
    game = BJ_GAMES.get(user_id)
    if not game: return
    p_hand = ", ".join(game["player_hand"])
    d_card = game["dealer_hand"][0]
    pval = calc_hand(game["player_hand"])
    text = f"🃏 <b>БЛЭКДЖЕК</b>\n\n💸 Ставка: <b>{game['bet']} ₣</b>\n\n🏦 Дилер: {d_card}, 🂠 (?)\n👤 Ты: {p_hand} <b>({pval})</b>\n\nТвой ход:"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👇 Ещё карту", callback_data=BjCb(act="hit").pack()), InlineKeyboardButton(text="✋ Хватит", callback_data=BjCb(act="stand").pack())]])
    await message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(BjCb.filter())
async def cb_bj_handler(callback: CallbackQuery, callback_data: BjCb, casino_service: CasinoService):
    user_id = callback.from_user.id
    if user_id not in BJ_GAMES: return await callback.answer("Игра закончена!", show_alert=True)
    game = BJ_GAMES[user_id]
    act = callback_data.act
    if act == "hit":
        game["player_hand"].append(game["deck"].pop())
        pval = calc_hand(game["player_hand"])
        if pval > 21: await finish_blackjack(callback, user_id, "bust", casino_service)
        elif pval == 21: await finish_blackjack(callback, user_id, "stand", casino_service)
        else: await render_blackjack(callback.message, user_id)
    elif act == "stand": await finish_blackjack(callback, user_id, "stand", casino_service)

async def finish_blackjack(callback: CallbackQuery, user_id: int, reason: str, casino_service: CasinoService):
    bot = callback.bot
    chat_id = callback.message.chat.id
    game = BJ_GAMES.pop(user_id)
    bet = game["bet"]
    p_hand = game["player_hand"]
    d_hand = game["dealer_hand"]
    deck = game["deck"]
    msg_id = game.get("msg_id")
    pval = calc_hand(p_hand)
    if reason == "bust": mult, res_msg = 0.0, "💥 Перебор! Ты проиграл."
    elif reason == "bj": mult, res_msg = 2.5, "🎉 БЛЭКДЖЕК с раздачи! Чистая победа! (x2.5)"
    else:
        dval = calc_hand(d_hand)
        while dval < 17:
            d_hand.append(deck.pop())
            dval = calc_hand(d_hand)
        if dval > 21: mult, res_msg = 2.0, "🔥 Дилер перебрал! Ты выиграл! (x2)"
        elif pval > dval: mult, res_msg = 2.0, "🏆 Ты победил дилера! (x2)"
        elif pval == dval: mult, res_msg = 1.0, "🤝 Ничья! Ставка возвращена."
        else: mult, res_msg = 0.0, "😔 Дилер оказался сильнее. Ставка сгорела."
    win_amount = int(bet * mult)
    await casino_service.credit_win(user_id, win_amount)
    p_str = ", ".join(p_hand)
    d_str = ", ".join(d_hand)
    dval = calc_hand(d_hand)
    text = f"🃏 <b>БЛЭКДЖЕК: ИТОГИ</b>\n\n🏦 Дилер: {d_str} <b>({dval})</b>\n👤 Ты: {p_str} <b>({pval})</b>\n\n{res_msg}\n💸 Выигрыш: <b>{win_amount} ₣</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить", callback_data=CasinoCb(act="play", game="bj", val=str(bet)).pack())], [InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())]])
    try: await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb, parse_mode="HTML")
    except: pass

@router.message(lambda msg: is_cmd(msg.text, ["блекджек", "блэкджек", "21", "очко"]))
async def cmd_bj_direct(message: Message, casino_service: CasinoService):
    user_id = message.from_user.id
    parts = message.text.lower().split()
    try:
        balance = await casino_service.get_balance(user_id)
        if len(parts) > 1 and (parts[1].isdigit() or parts[1] == "all"):
            val = parts[1]
            bet = balance if val == "all" else int(val)
            if bet < 10: return await message.answer("Минимальная ставка 10 ₣!")
            if balance < bet: return await message.answer("Недостаточно средств!")
            class FakeCb:
                def __init__(self, msg):
                    self.message = msg
                    self.from_user = msg.from_user
                    self.bot = msg.bot
            await start_blackjack(FakeCb(message), user_id, bet, casino_service)
        else:
            sent_msg = await message.answer("🃏 <b>БЛЭКДЖЕК</b>\n\nВыберите размер ставки:", reply_markup=kb_casino_bet("bj"), parse_mode="HTML")
            await cleanup_old_game(message.bot, message.chat.id, user_id)
            LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
            asyncio.create_task(delete_later(sent_msg))
    except UserNotRegisteredError as e:
        sent = await message.answer(str(e))
        asyncio.create_task(delete_later(sent, 60))

@router.message(lambda msg: is_cmd(msg.text, ["сапер", "saper", "сапёр"]))
async def cmd_saper(message: Message, casino_service: CasinoService):
    user_id = message.from_user.id
    parts = message.text.lower().split()[1:]
    bet_str = None
    diff = None
    diff_synonyms = {"easy": ["легкий", "изи", "easy", "легко", "1"], "medium": ["средний", "нормальный", "med", "medium", "норм", "2"], "hard": ["трудный", "сложный", "hard", "хард", "3"]}
    for part in parts:
        if part.isdigit() or part in ["all", "все", "всё"]: bet_str = "all" if part in ["all", "все", "всё"] else part
        else:
            for d_key, syns in diff_synonyms.items():
                if part in syns:
                    diff = d_key
                    break
    await cleanup_old_game(message.bot, message.chat.id, user_id)
    if not bet_str:
        sent_msg = await message.answer("💣 <b>САПЕР</b>\n\nВыберите сумму ставки (мин. 10 ₣):", reply_markup=kb_saper_setup_bet(), parse_mode="HTML")
        LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
        asyncio.create_task(delete_later(sent_msg))
        return
    if not diff:
        sent_msg = await message.answer(f"💣 <b>САПЕР</b>\n\nСтавка: <b>{bet_str}</b> ₣\nВыберите сложность:", reply_markup=kb_saper_setup_diff(bet_str), parse_mode="HTML")
        LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
        asyncio.create_task(delete_later(sent_msg))
        return
    await start_saper_game(message.chat.id, user_id, message.from_user.full_name, bet_str, diff, casino_service, bot_msg=message)

async def start_saper_game(chat_id: int, user_id: int, user_name: str, bet_str: str, diff: str, casino_service: CasinoService, bot_msg=None):
    bot = bot_msg.bot if hasattr(bot_msg, 'bot') else getattr(bot_msg.message, 'bot', None)
    await cleanup_old_game(bot, chat_id, user_id)
    async def send_error(txt):
        if isinstance(bot_msg, Message):
            msg = await bot_msg.answer(txt)
            asyncio.create_task(delete_later(msg, 60))
        elif isinstance(bot_msg, CallbackQuery): await bot_msg.message.edit_text(txt)
    try:
        balance = await casino_service.get_balance(user_id)
        bet = balance if bet_str == "all" else int(bet_str)
        if bet < 10: return await send_error("❌ Минимальная ставка в сапере — <b>10</b> ₣.")
        await casino_service.charge_bet(user_id, bet)
        mines_count = SAPER_DIFFS[diff]["mines"]
        grid = [0] * 25
        mine_indices = random.sample(range(25), mines_count)
        for i in mine_indices: grid[i] = 1
        SAPER_GAMES[user_id] = {"chat_id": chat_id, "name": user_name, "bet": bet, "diff": diff, "grid": grid, "clicked": [], "mult": 1.0}
        text = f"💣 <b>САПЕР</b> 💣\n\n👤 Игрок: <b>{user_name}</b>\n🕹 Сложность: <b>{SAPER_DIFFS[diff]['name']}</b>\n💸 Ставка: <b>{bet}</b> ₣\n\n<i>Открывай ячейки, но берегись мин!</i>"
        if isinstance(bot_msg, CallbackQuery):
            try: await bot_msg.message.delete()
            except: pass
        sent_msg = await bot.send_message(chat_id, text, reply_markup=kb_saper_game(SAPER_GAMES[user_id]), parse_mode="HTML")
        LAST_GAME_MSGS[user_id] = [sent_msg.message_id]
        asyncio.create_task(delete_later(sent_msg))
    except (UserNotRegisteredError, NotEnoughMoneyError) as e:
        await send_error(str(e))

@router.callback_query(SaperSetupCb.filter())
async def cb_saper_setup(callback: CallbackQuery, callback_data: SaperSetupCb, casino_service: CasinoService):
    user_id = callback.from_user.id
    act = callback_data.act
    val = callback_data.val
    if act == "cancel": return await callback.message.delete()
    if act == "bet": await callback.message.edit_text(f"💣 <b>САПЕР</b>\n\nСтавка: <b>{val}</b> ₣\nВыберите сложность:", reply_markup=kb_saper_setup_diff(val), parse_mode="HTML")
    elif act.startswith("start_"):
        bet_str = act.split("_")[1]
        await start_saper_game(callback.message.chat.id, user_id, callback.from_user.full_name, bet_str, val, casino_service, bot_msg=callback)

@router.callback_query(SaperCb.filter())
async def cb_saper_play(callback: CallbackQuery, callback_data: SaperCb, casino_service: CasinoService):
    user_id = callback.from_user.id
    game = SAPER_GAMES.get(user_id)
    if callback_data.act == "ignore": return await callback.answer()
    if not game or game["chat_id"] != callback.message.chat.id: return await callback.answer("❌ Это не ваша игра или она уже завершена!", show_alert=True)
    act = callback_data.act
    idx = callback_data.idx
    if act == "cashout":
        win_amount = int(game["bet"] * game["mult"])
        await casino_service.credit_win(user_id, win_amount)
        text = f"💰 <b>ДЕНЬГИ СНЯТЫ!</b>\n\n👤 Игрок: <b>{game['name']}</b>\n🕹 Сложность: <b>{SAPER_DIFFS[game['diff']]['name']}</b>\n📥 Забрано: <b>{win_amount} ₣</b> (x{game['mult']:.1f})"
        kb = kb_saper_game(game, game_over=True)
        kb.inline_keyboard.append([InlineKeyboardButton(text="🔄 Повторить партию", callback_data=SaperSetupCb(act=f"start_{game['bet']}", val=game['diff']).pack())])
        kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        del SAPER_GAMES[user_id]
        return
    if act == "click":
        if idx in game["clicked"]: return await callback.answer("Эта ячейка уже открыта!", show_alert=False)
        if game["grid"][idx] == 1:
            game["clicked"].append(idx)
            text = f"💥 <b>БУМ! ВЫ ПРОИГРАЛИ!</b> 💥\n\n👤 Игрок: <b>{game['name']}</b>\n💸 Потеряно: <b>{game['bet']} ₣</b>\n<i>Мина оказалась прямо под ногой...</i>"
            kb = kb_saper_game(game, game_over=True)
            kb.inline_keyboard.append([InlineKeyboardButton(text="🔄 Повторить партию", callback_data=SaperSetupCb(act=f"start_{game['bet']}", val=game['diff']).pack())])
            kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())])
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            del SAPER_GAMES[user_id]
            return
        game["clicked"].append(idx)
        game["mult"] += SAPER_DIFFS[game["diff"]]["mult_step"]
        safe_total = SAPER_DIFFS[game["diff"]]["safe"]
        if len(game["clicked"]) == safe_total:
            win_amount = int(game["bet"] * game["mult"])
            await casino_service.credit_win(user_id, win_amount)
            text = f"🏆 <b>ИДЕАЛЬНАЯ ПОБЕДА!</b> 🏆\n\n👤 Игрок: <b>{game['name']}</b>\n🎉 Все безопасные ячейки найдены!\n🤑 Выигрыш: <b>{win_amount} ₣</b> (x{game['mult']:.1f})"
            kb = kb_saper_game(game, game_over=True)
            kb.inline_keyboard.append([InlineKeyboardButton(text="🔄 Повторить партию", callback_data=SaperSetupCb(act=f"start_{game['bet']}", val=game['diff']).pack())])
            kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())])
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            del SAPER_GAMES[user_id]
            return
        current_win = int(game["bet"] * game["mult"])
        text = f"💣 <b>САПЕР</b> 💣\n\n👤 Игрок: <b>{game['name']}</b>\n🕹 Сложность: <b>{SAPER_DIFFS[game['diff']]['name']}</b>\n💸 Ставка: <b>{game['bet']}</b> ₣\n💰 Выигрыш: <b>{current_win} ₣</b> (x{game['mult']:.2f})\n\n<i>Играем дальше или забираем?</i>"
        try: await callback.message.edit_text(text, reply_markup=kb_saper_game(game), parse_mode="HTML")
        except: pass