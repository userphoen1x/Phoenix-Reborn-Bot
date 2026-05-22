import asyncio
import random
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from utils.database import get_eco_data, update_balance, set_eco_data

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


def get_class_bonus(bot_class: str):
    if bot_class == "Махим": return {"work_cd": 4, "luck": 0.10, "rob_mult": 1.0}
    if bot_class == "Спырту": return {"work_cd": 3, "luck": -0.05, "rob_mult": 1.5}
    if bot_class == "Ванёк": return {"work_cd": 5, "luck": 0.20, "rob_mult": 1.0}
    return {"work_cd": 4, "luck": 0.0, "rob_mult": 1.0}


@router.message(F.text.lower().in_({"работа", "ворк"}))
async def cmd_work(message: Message):
    user_id = message.from_user.id
    eco = await get_eco_data(user_id)
    if not eco: return

    bonuses = get_class_bonus(eco["bot_class"])
    cd_hours = bonuses["work_cd"]

    now = datetime.now()
    if eco["last_work"]:
        last_work = datetime.fromisoformat(eco["last_work"])
        diff = now - last_work
        if diff < timedelta(hours=cd_hours):
            rem = timedelta(hours=cd_hours) - diff
            mm, ss = divmod(int(rem.total_seconds()), 60)
            hh, mm = divmod(mm, 60)
            await message.answer(f"⏳ Ожидание... Вы сможете работать через <b>{hh}ч {mm}м</b>.", parse_mode="HTML")
            return

    reward = random.randint(50, 150)
    await update_balance(user_id, reward)
    await set_eco_data(user_id, "last_work", now.isoformat())
    await message.answer(f"✅ <b>УСПЕШНО!</b>\n🔥 Вы поработали и заработали <b>{reward}</b> ₣!", parse_mode="HTML")


@router.message(lambda msg: msg.text and msg.text.lower().startswith(("перевод", "перевести", "pay", "/pay")))
async def cmd_pay(message: Message, bot: Bot):
    parts = message.text.split()
    if not parts: return

    target_id = None
    target_name = None
    idx = 1

    if idx < len(parts) and parts[idx].startswith("@"):
        target_username = parts[idx]
        idx += 1
        db_path = "/app/data/bot_data_v3.db"
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT user_id FROM tg_profiles WHERE full_name = ? COLLATE NOCASE",
                                  (target_username,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    target_id = row[0]
                    target_name = target_username
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        u = message.reply_to_message.from_user
        target_name = f"@{u.username}" if u.username else u.full_name

    if not target_id:
        await message.answer("❌ Не удалось найти пользователя. Укажите @username или ответьте на его сообщение.")
        return

    if idx >= len(parts) or not parts[idx].isdigit():
        await message.answer("❌ Укажите сумму перевода числом. Пример: <code>перевод 100</code>", parse_mode="HTML")
        return

    amount = int(parts[idx])
    if amount <= 0: return

    sender_id = message.from_user.id
    if sender_id == target_id:
        await message.answer("❌ Нельзя переводить Феники самому себе.")
        return

    eco_sender = await get_eco_data(sender_id)
    if not eco_sender or eco_sender["balance"] < amount:
        await message.answer("❌ Недостаточно средств.")
        return

    eco_target = await get_eco_data(target_id)
    if not eco_target:
        await message.answer("❌ Этот пользователь еще не зарегистрирован в экономической системе бота.")
        return

    await update_balance(sender_id, -amount)
    await update_balance(target_id, amount)
    await message.answer(f"✅ <b>Перевод выполнен!</b>\n\n👤 Кому: <b>{target_name}</b>\n💸 Сумма: <b>{amount}</b> ₣",
                         parse_mode="HTML")


# ==========================================
# ИГРЫ: КАЗИНО ХАБ И TG ЭМОДЗИ
# ==========================================

class CasinoCb(CallbackData, prefix="cas"):
    act: str
    game: str
    val: str = "0"


def kb_casino_main(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Блэкджек (21)", callback_data=CasinoCb(act="bet", game="bj").pack()),
         InlineKeyboardButton(text="💣 Сапёр", callback_data=CasinoCb(act="saper_route", game="saper").pack())],
        [InlineKeyboardButton(text="🎰 Слоты", callback_data=CasinoCb(act="bet", game="slot").pack()),
         InlineKeyboardButton(text="🎲 Кости", callback_data=CasinoCb(act="bet", game="dice").pack())],
        [InlineKeyboardButton(text="🎯 Дартс", callback_data=CasinoCb(act="bet", game="darts").pack()),
         InlineKeyboardButton(text="🎳 Боулинг", callback_data=CasinoCb(act="bet", game="bowl").pack())],
        [InlineKeyboardButton(text="⚽️ Футбол", callback_data=CasinoCb(act="bet", game="fball").pack()),
         InlineKeyboardButton(text="🏀 Баскетбол", callback_data=CasinoCb(act="bet", game="bball").pack())],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data=CasinoCb(act="close", game="none").pack())]
    ])


def kb_casino_bet(user_id: int, game: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 10", callback_data=CasinoCb(act="play", game=game, val="10").pack()),
         InlineKeyboardButton(text="💵 50", callback_data=CasinoCb(act="play", game=game, val="50").pack()),
         InlineKeyboardButton(text="💵 100", callback_data=CasinoCb(act="play", game=game, val="100").pack())],
        [InlineKeyboardButton(text="💸 500", callback_data=CasinoCb(act="play", game=game, val="500").pack()),
         InlineKeyboardButton(text="💸 1000", callback_data=CasinoCb(act="play", game=game, val="1000").pack()),
         InlineKeyboardButton(text="🏦 ВА-БАНК", callback_data=CasinoCb(act="play", game=game, val="all").pack())],
        [InlineKeyboardButton(text="⬅️ Назад к играм", callback_data=CasinoCb(act="menu", game="none").pack())]
    ])


@router.message(lambda msg: msg.text and msg.text.lower() in ["казик", "казино", "игра", "игры", "casino", "games"])
async def cmd_casino_main(message: Message):
    user_id = message.from_user.id
    eco = await get_eco_data(user_id)
    if not eco:
        return await message.answer("❌ У вас нет счета. Зарегистрируйтесь в боте.")

    await message.answer(
        f"🎰 <b>КАЗИНО PHOENIX</b> 🎰\n\n"
        f"💰 Твой баланс: <b>{eco['balance']}</b> ₣\n\n"
        f"Выбери игру, чтобы испытать удачу:",
        reply_markup=kb_casino_main(user_id),
        parse_mode="HTML"
    )


async def run_emoji_game(target, user_id: int, game: str, bet: int, guess: int = None):
    emoji_map = {"slot": "🎰", "dice": "🎲", "darts": "🎯", "bowl": "🎳", "fball": "⚽", "bball": "🏀"}
    emj = emoji_map[game]

    guess_text = f" Ты ставил на число <b>{guess}</b>." if game == "dice" else ""
    msg_text = f"{emj} Ставка <b>{bet}</b> ₣ принята!{guess_text}\nБросаю..."

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(msg_text, parse_mode="HTML")
        dice_msg = await target.message.answer_dice(emoji=emj)
    else:
        await target.answer(msg_text, parse_mode="HTML")
        dice_msg = await target.answer_dice(emoji=emj)

    await asyncio.sleep(4.0 if game in ["slot", "bowl", "fball", "bball"] else 3.0)

    val_res = dice_msg.dice.value
    mult = 0.0
    msg_result = "Увы, ставка сгорела. 😔"

    if game == "slot":
        if val_res == 64:
            mult, msg_result = 10.0, "ДЖЕКПОТ! 777! 🎉 (x10)"
        elif val_res in [1, 22, 43]:
            mult, msg_result = 5.0, "Три в ряд! Отличный куш! 🍒 (x5)"
    elif game == "dice":
        if val_res == guess:
            mult, msg_result = 5.0, f"Угадал! Выпало {val_res}! 🎲🎉 (x5)"
        else:
            msg_result = f"Мимо. Выпало {val_res}, а ты ставил на {guess}. 😔"
    elif game in ["darts", "bowl"]:
        if val_res == 6: mult, msg_result = 3.0, "Прямо в цель! Идеально! 🏆 (x3)"
    elif game in ["fball", "bball"]:
        if val_res in [4, 5]: mult, msg_result = 2.0, "ГООООЛ! / Точно в корзину! 🏆 (x2)"

    win_amount = int(bet * mult)
    if win_amount > 0:
        await update_balance(user_id, win_amount)

    res_text = (
        f"{emj} <b>РЕЗУЛЬТАТ: {val_res}</b>\n\n"
        f"{msg_result}\n"
        f"💸 Выигрыш: <b>{win_amount} ₣</b>\n"
    )

    retry_val = str(bet) if game != "dice" else f"{bet}_{guess}"
    kb_retry = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Повторить партию",
                              callback_data=CasinoCb(act="play", game=game, val=retry_val).pack())],
        [InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())]
    ])

    if isinstance(target, CallbackQuery):
        await target.message.answer(res_text, reply_markup=kb_retry, parse_mode="HTML")
    else:
        await target.answer(res_text, reply_markup=kb_retry, parse_mode="HTML")


@router.callback_query(CasinoCb.filter())
async def cb_casino_handler(callback: CallbackQuery, callback_data: CasinoCb):
    user_id = callback.from_user.id
    act = callback_data.act
    game = callback_data.game
    val = callback_data.val

    if act == "close":
        await callback.message.delete()
        return

    if act == "menu":
        eco = await get_eco_data(user_id)
        await callback.message.edit_text(
            f"🎰 <b>КАЗИНО PHOENIX</b> 🎰\n\n"
            f"💰 Твой баланс: <b>{eco['balance']}</b> ₣\n\n"
            f"Выбери игру, чтобы испытать удачу:",
            reply_markup=kb_casino_main(user_id),
            parse_mode="HTML"
        )
        return

    if act == "saper_route":
        await callback.message.edit_text("💣 <b>САПЕР</b>\n\nВыберите сумму ставки (мин. 10 ₣):",
                                         reply_markup=kb_saper_setup_bet(user_id), parse_mode="HTML")
        return

    if act == "bet":
        game_names = {"bj": "🃏 Блэкджек", "slot": "🎰 Слоты", "dice": "🎲 Кости", "darts": "🎯 Дартс", "bowl": "🎳 Боулинг",
                      "fball": "⚽️ Футбол", "bball": "🏀 Баскетбол"}
        await callback.message.edit_text(
            f"{game_names[game]}\n\nВыберите размер ставки:",
            reply_markup=kb_casino_bet(user_id, game),
            parse_mode="HTML"
        )
        return

    if act == "play" and game == "dice" and "_" not in val:
        eco = await get_eco_data(user_id)
        bet = eco['balance'] if val == "all" else int(val)
        if eco['balance'] < bet: return await callback.answer("Недостаточно средств!", show_alert=True)

        kb_dice_guess = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_1").pack()),
             InlineKeyboardButton(text="2️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_2").pack()),
             InlineKeyboardButton(text="3️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_3").pack())],
            [InlineKeyboardButton(text="4️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_4").pack()),
             InlineKeyboardButton(text="5️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_5").pack()),
             InlineKeyboardButton(text="6️⃣", callback_data=CasinoCb(act="play", game="dice", val=f"{bet}_6").pack())],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=CasinoCb(act="bet", game="dice").pack())]
        ])
        await callback.message.edit_text(
            f"🎲 Ставка: <b>{bet} ₣</b>\n\nНа какое число ставишь? (Угадаешь — заберешь x5!)",
            reply_markup=kb_dice_guess, parse_mode="HTML")
        return

    if act == "play":
        eco = await get_eco_data(user_id)
        if not eco: return
        bal = eco['balance']

        if game == "dice":
            bet_str, guess_str = val.split("_")
            bet = int(bet_str)
            guess = int(guess_str)
        else:
            bet = bal if val == "all" else int(val)
            guess = None

        if bal < bet: return await callback.answer("Недостаточно средств!", show_alert=True)

        if game == "bj":
            await start_blackjack(callback, user_id, bet)
            return

        await run_emoji_game(callback, user_id, game, bet, guess)


# Текстовые триггеры синонимов для моментального вызова
@router.message(lambda msg: msg.text and msg.text.lower().split()[0] in [
    "слоты", "слот", "slots", "slot", "кости", "кубик", "кубики", "dice",
    "дартс", "darts", "боулинг", "боул", "bowling", "bowl",
    "футбол", "ногомяч", "football", "fball", "баскетбол", "баскет", "basketball", "bball"
])
async def cmd_direct_games(message: Message):
    user_id = message.from_user.id
    eco = await get_eco_data(user_id)
    if not eco: return

    parts = message.text.lower().split()
    cmd = parts[0]

    game = "slot" if any(x in cmd for x in ["слот", "slot"]) else \
        "dice" if any(x in cmd for x in ["кост", "кубик", "dice"]) else \
            "darts" if any(x in cmd for x in ["дартс", "darts"]) else \
                "bowl" if any(x in cmd for x in ["боул", "bowl"]) else \
                    "fball" if any(x in cmd for x in ["футб", "ногом", "fball"]) else "bball"

    bet_str = None
    for p in parts[1:]:
        if p.isdigit() or p in ["all", "все", "всё"]:
            bet_str = "all" if p in ["all", "все", "всё"] else p
            break

    if not bet_str:
        game_names = {"slot": "🎰 Слоты", "dice": "🎲 Кости", "darts": "🎯 Дартс", "bowl": "🎳 Боулинг",
                      "fball": "⚽️ Футбол", "bball": "🏀 Баскетбол"}
        return await message.answer(f"{game_names[game]}\n\nВыберите размер ставки:",
                                    reply_markup=kb_casino_bet(user_id, game), parse_mode="HTML")

    bet = eco['balance'] if bet_str == "all" else int(bet_str)
    if bet < 10: return await message.answer("Минимальная ставка 10 ₣!")
    if eco['balance'] < bet: return await message.answer("Недостаточно средств!")

    if game == "dice":
        guess = None
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
            return await message.answer(
                f"🎲 Ставка: <b>{bet} ₣</b>\n\nНа какое число ставишь? (Угадаешь — заберешь x5!)",
                reply_markup=kb_dice_guess, parse_mode="HTML")
        else:
            await run_emoji_game(message, user_id, game, bet, guess)
    else:
        await run_emoji_game(message, user_id, game, bet)


# ==========================================
# ИГРА: БЛЭКДЖЕК (21)
# ==========================================

BJ_GAMES = {}


class BjCb(CallbackData, prefix="bj"):
    act: str


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


async def start_blackjack(callback: CallbackQuery, user_id: int, bet: int):
    await update_balance(user_id, -bet)

    deck = get_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    BJ_GAMES[user_id] = {
        "bet": bet,
        "deck": deck,
        "player_hand": player_hand,
        "dealer_hand": dealer_hand
    }

    pval = calc_hand(player_hand)
    if pval == 21:
        await finish_blackjack(callback, user_id, "bj")
        return

    await render_blackjack(callback.message, user_id)


async def render_blackjack(message: Message, user_id: int):
    game = BJ_GAMES.get(user_id)
    if not game: return

    p_hand = ", ".join(game["player_hand"])
    d_card = game["dealer_hand"][0]
    pval = calc_hand(game["player_hand"])

    text = (
        f"🃏 <b>БЛЭКДЖЕК</b>\n\n"
        f"💸 Ставка: <b>{game['bet']} ₣</b>\n\n"
        f"🏦 Дилер: {d_card}, 🂠 (?)\n"
        f"👤 Ты: {p_hand} <b>({pval})</b>\n\n"
        f"Твой ход:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👇 Ещё карту (Hit)", callback_data=BjCb(act="hit").pack()),
         InlineKeyboardButton(text="✋ Хватит (Stand)", callback_data=BjCb(act="stand").pack())]
    ])

    if isinstance(message, Message):
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(BjCb.filter())
async def cb_bj_handler(callback: CallbackQuery, callback_data: BjCb):
    user_id = callback.from_user.id
    if user_id not in BJ_GAMES:
        return await callback.answer("Игра устарела или уже закончена!", show_alert=True)

    game = BJ_GAMES[user_id]
    act = callback_data.act

    if act == "hit":
        game["player_hand"].append(game["deck"].pop())
        pval = calc_hand(game["player_hand"])
        if pval > 21:
            await finish_blackjack(callback, user_id, "bust")
        elif pval == 21:
            await finish_blackjack(callback, user_id, "stand")
        else:
            await render_blackjack(callback.message, user_id)

    elif act == "stand":
        await finish_blackjack(callback, user_id, "stand")


async def finish_blackjack(callback: CallbackQuery, user_id: int, reason: str):
    game = BJ_GAMES.pop(user_id)
    bet = game["bet"]
    p_hand = game["player_hand"]
    d_hand = game["dealer_hand"]
    deck = game["deck"]

    pval = calc_hand(p_hand)

    if reason == "bust":
        mult = 0.0
        res_msg = "💥 Перебор! Ты проиграл."
    elif reason == "bj":
        mult = 2.5
        res_msg = "🎉 БЛЭКДЖЕК с раздачи! Чистая победа! (x2.5)"
    else:
        dval = calc_hand(d_hand)
        while dval < 17:
            d_hand.append(deck.pop())
            dval = calc_hand(d_hand)

        if dval > 21:
            mult = 2.0
            res_msg = "🔥 Дилер перебрал! Ты выиграл! (x2)"
        elif pval > dval:
            mult = 2.0
            res_msg = "🏆 Ты победил дилера! (x2)"
        elif pval == dval:
            mult = 1.0
            res_msg = "🤝 Ничья! Ставка возвращена."
        else:
            mult = 0.0
            res_msg = "😔 Дилер оказался сильнее. Ставка сгорела."

    win_amount = int(bet * mult)
    if win_amount > 0:
        await update_balance(user_id, win_amount)

    p_str = ", ".join(p_hand)
    d_str = ", ".join(d_hand)
    dval = calc_hand(d_hand)

    text = (
        f"🃏 <b>БЛЭКДЖЕК: ИТОГИ</b>\n\n"
        f"🏦 Дилер: {d_str} <b>({dval})</b>\n"
        f"👤 Ты: {p_str} <b>({pval})</b>\n\n"
        f"{res_msg}\n"
        f"💸 Выигрыш: <b>{win_amount} ₣</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Повторить партию",
                              callback_data=CasinoCb(act="play", game="bj", val=str(bet)).pack())],
        [InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.message(
    lambda msg: msg.text and msg.text.lower().split()[0] in ["блекджек", "блэкджек", "21", "очко", "двадцатьодно",
                                                             "двадцать", "очко"])
async def cmd_bj_direct(message: Message):
    user_id = message.from_user.id
    eco = await get_eco_data(user_id)
    if not eco: return

    parts = message.text.lower().split()
    if len(parts) > 1 and (parts[1].isdigit() or parts[1] == "all"):
        val = parts[1]
        bal = eco['balance']
        bet = bal if val == "all" else int(val)

        if bet < 10: return await message.answer("Минимальная ставка 10 ₣!")
        if bal < bet: return await message.answer("Недостаточно средств!")

        class FakeCb:
            def __init__(self, msg):
                self.message = msg
                self.from_user = msg.from_user

        sent_msg = await message.answer("Раздаю карты...")
        await start_blackjack(FakeCb(sent_msg), user_id, bet)
    else:
        await message.answer("🃏 <b>БЛЭКДЖЕК</b>\n\nВыберите размер ставки:", reply_markup=kb_casino_bet(user_id, "bj"),
                             parse_mode="HTML")


# ==========================================
# ИГРА: САПЕР
# ==========================================

class SaperSetupCb(CallbackData, prefix="spset"):
    act: str
    val: str


class SaperCb(CallbackData, prefix="sap"):
    act: str
    idx: int


SAPER_GAMES = {}

SAPER_DIFFS = {
    "easy": {"name": "🟢 Легкий", "mines": 5, "mult_step": 0.2, "safe": 20},
    "medium": {"name": "🟡 Средний", "mines": 12, "mult_step": 0.5, "safe": 13},
    "hard": {"name": "🔴 Трудный", "mines": 20, "mult_step": 1.5, "safe": 5}
}


def kb_saper_setup_bet(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 50", callback_data=SaperSetupCb(act="bet", val="50").pack()),
         InlineKeyboardButton(text="💵 100", callback_data=SaperSetupCb(act="bet", val="100").pack())],
        [InlineKeyboardButton(text="💸 500", callback_data=SaperSetupCb(act="bet", val="500").pack()),
         InlineKeyboardButton(text="💸 1000", callback_data=SaperSetupCb(act="bet", val="1000").pack())],
        [InlineKeyboardButton(text="🏦 ВА-БАНК", callback_data=SaperSetupCb(act="bet", val="all").pack())],
        [InlineKeyboardButton(text="⬅️ Назад к играм", callback_data=CasinoCb(act="menu", game="none").pack())]
    ])


def kb_saper_setup_diff(user_id: int, bet: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Легкий (5 мин)",
                              callback_data=SaperSetupCb(act=f"start_{bet}", val="easy").pack())],
        [InlineKeyboardButton(text="🟡 Средний (12 мин)",
                              callback_data=SaperSetupCb(act=f"start_{bet}", val="medium").pack())],
        [InlineKeyboardButton(text="🔴 Трудный (20 мин)",
                              callback_data=SaperSetupCb(act=f"start_{bet}", val="hard").pack())],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=SaperSetupCb(act="cancel", val="0").pack())]
    ])


def kb_saper_game(user_id: int, game_over=False):
    game = SAPER_GAMES.get(user_id)
    if not game: return None

    kb = []
    grid = game["grid"]
    clicked = game["clicked"]

    for row in range(5):
        row_btns = []
        for col in range(5):
            idx = row * 5 + col
            if not game_over:
                text = "💎" if idx in clicked else "⬜️"
                cb = SaperCb(act="click", idx=idx).pack()
            else:
                if grid[idx] == 1:
                    text = "💥" if idx in clicked else "💣"
                else:
                    text = "💎" if idx in clicked else "⬜️"
                cb = "ignore"
            row_btns.append(InlineKeyboardButton(text=text, callback_data=cb))
        kb.append(row_btns)

    if not game_over and len(clicked) > 0:
        current_win = int(game["bet"] * game["mult"])
        kb.append([InlineKeyboardButton(text=f"🛑 Забрать {current_win} ₣",
                                        callback_data=SaperCb(act="cashout", idx=-1).pack())])

    return InlineKeyboardMarkup(inline_keyboard=kb)


@router.message(lambda msg: msg.text and msg.text.lower().startswith(("сапер", "saper", "сапёр")))
async def cmd_saper(message: Message):
    user_id = message.from_user.id
    parts = message.text.lower().split()[1:]

    bet_str = None
    diff = None

    diff_synonyms = {
        "easy": ["легкий", "изи", "easy", "легко", "1"],
        "medium": ["средний", "нормальный", "med", "medium", "норм", "2"],
        "hard": ["трудный", "сложный", "hard", "хард", "3"]
    }

    for part in parts:
        if part.isdigit() or part in ["all", "все", "всё"]:
            bet_str = "all" if part in ["all", "все", "всё"] else part
        else:
            for d_key, syns in diff_synonyms.items():
                if part in syns:
                    diff = d_key
                    break

    if not bet_str:
        await message.answer("💣 <b>САПЕР</b>\n\nВыберите сумму ставки (мин. 10 ₣):",
                             reply_markup=kb_saper_setup_bet(user_id), parse_mode="HTML")
        return

    if not diff:
        await message.answer(f"💣 <b>САПЕР</b>\n\nСтавка: <b>{bet_str}</b> ₣\nВыберите сложность:",
                             reply_markup=kb_saper_setup_diff(user_id, bet_str), parse_mode="HTML")
        return

    await start_saper_game(message.chat.id, user_id, message.from_user.full_name, bet_str, diff, bot_msg=message)


async def start_saper_game(chat_id: int, user_id: int, user_name: str, bet_str: str, diff: str, bot_msg=None):
    eco = await get_eco_data(user_id)

    async def send_error(txt):
        if isinstance(bot_msg, Message):
            await bot_msg.answer(txt)
        elif isinstance(bot_msg, CallbackQuery):
            await bot_msg.message.edit_text(txt)

    if not eco:
        await send_error("❌ У вас нет счета. Зарегистрируйтесь в боте.")
        return

    bal = eco["balance"]
    if bet_str == "all":
        bet = bal
    else:
        bet = int(bet_str)

    if bet < 10:
        await send_error("❌ Минимальная ставка в сапере — <b>10</b> ₣.")
        return

    if bal < bet:
        await send_error("❌ Недостаточно средств для этой ставки.")
        return

    await update_balance(user_id, -bet)

    mines_count = SAPER_DIFFS[diff]["mines"]
    grid = [0] * 25
    mine_indices = random.sample(range(25), mines_count)
    for i in mine_indices:
        grid[i] = 1

    SAPER_GAMES[user_id] = {
        "chat_id": chat_id,
        "name": user_name,
        "bet": bet,
        "diff": diff,
        "grid": grid,
        "clicked": [],
        "mult": 1.0
    }

    text = (
        f"💣 <b>САПЕР</b> 💣\n\n"
        f"👤 Игрок: <b>{user_name}</b>\n"
        f"🕹 Сложность: <b>{SAPER_DIFFS[diff]['name']}</b>\n"
        f"💸 Ставка: <b>{bet}</b> ₣\n\n"
        f"<i>Открывай ячейки, но берегись мин!</i>"
    )

    kb = kb_saper_game(user_id)
    if isinstance(bot_msg, Message):
        await bot_msg.answer(text, reply_markup=kb, parse_mode="HTML")
    elif isinstance(bot_msg, CallbackQuery):
        await bot_msg.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(SaperSetupCb.filter())
async def cb_saper_setup(callback: CallbackQuery, callback_data: SaperSetupCb):
    user_id = callback.from_user.id
    act = callback_data.act
    val = callback_data.val

    if act == "cancel":
        await callback.message.delete()
        return

    if act == "bet":
        await callback.message.edit_text(f"💣 <b>САПЕР</b>\n\nСтавка: <b>{val}</b> ₣\nВыберите сложность:",
                                         reply_markup=kb_saper_setup_diff(user_id, val), parse_mode="HTML")

    elif act.startswith("start_"):
        bet_str = act.split("_")[1]
        diff = val
        await start_saper_game(callback.message.chat.id, user_id, callback.from_user.full_name, bet_str, diff,
                               bot_msg=callback)


@router.callback_query(SaperCb.filter())
async def cb_saper_play(callback: CallbackQuery, callback_data: SaperCb):
    user_id = callback.from_user.id
    game = SAPER_GAMES.get(user_id)

    if callback_data.act == "ignore":
        await callback.answer()
        return

    if not game or game["chat_id"] != callback.message.chat.id:
        await callback.answer("❌ Это не ваша игра или она уже завершена!", show_alert=True)
        return

    act = callback_data.act
    idx = callback_data.idx

    if act == "cashout":
        win_amount = int(game["bet"] * game["mult"])
        await update_balance(user_id, win_amount)

        text = (
            f"💰 <b>ДЕНЬГИ СНЯТЫ!</b>\n\n"
            f"👤 Игрок: <b>{game['name']}</b>\n"
            f"🕹 Сложность: <b>{SAPER_DIFFS[game['diff']]['name']}</b>\n"
            f"📥 Забрано: <b>{win_amount} ₣</b> (x{game['mult']:.1f})"
        )
        kb = kb_saper_game(user_id, game_over=True)
        kb.inline_keyboard.append([InlineKeyboardButton(text="🔄 Повторить партию",
                                                        callback_data=SaperSetupCb(act=f"start_{game['bet']}",
                                                                                   val=game['diff']).pack())])
        kb.inline_keyboard.append(
            [InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())])

        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        del SAPER_GAMES[user_id]
        return

    if act == "click":
        if idx in game["clicked"]:
            await callback.answer("Эта ячейка уже открыта!", show_alert=False)
            return

        if game["grid"][idx] == 1:
            game["clicked"].append(idx)
            text = (
                f"💥 <b>БУМ! ВЫ ПРОИГРАЛИ!</b> 💥\n\n"
                f"👤 Игрок: <b>{game['name']}</b>\n"
                f"💸 Потеряно: <b>{game['bet']} ₣</b>\n"
                f"<i>Мина оказалась прямо под ногой...</i>"
            )
            kb = kb_saper_game(user_id, game_over=True)
            kb.inline_keyboard.append([InlineKeyboardButton(text="🔄 Повторить партию",
                                                            callback_data=SaperSetupCb(act=f"start_{game['bet']}",
                                                                                       val=game['diff']).pack())])
            kb.inline_keyboard.append(
                [InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())])

            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            del SAPER_GAMES[user_id]
            return

        game["clicked"].append(idx)
        game["mult"] += SAPER_DIFFS[game["diff"]]["mult_step"]

        safe_total = SAPER_DIFFS[game["diff"]]["safe"]
        if len(game["clicked"]) == safe_total:
            win_amount = int(game["bet"] * game["mult"])
            await update_balance(user_id, win_amount)
            text = (
                f"🏆 <b>ИДЕАЛЬНАЯ ПОБЕДА!</b> 🏆\n\n"
                f"👤 Игрок: <b>{game['name']}</b>\n"
                f"🎉 Все безопасные ячейки найдены!\n"
                f"🤑 Выигрыш: <b>{win_amount} ₣</b> (x{game['mult']:.1f})"
            )
            kb = kb_saper_game(user_id, game_over=True)
            kb.inline_keyboard.append([InlineKeyboardButton(text="🔄 Повторить партию",
                                                            callback_data=SaperSetupCb(act=f"start_{game['bet']}",
                                                                                       val=game['diff']).pack())])
            kb.inline_keyboard.append(
                [InlineKeyboardButton(text="⬅️ Меню игр", callback_data=CasinoCb(act="menu", game="none").pack())])

            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            del SAPER_GAMES[user_id]
            return
        current_win = int(game["bet"] * game["mult"])
        text = (
            f"💣 <b>САПЕР</b> 💣\n\n"
            f"👤 Игрок: <b>{game['name']}</b>\n"
            f"🕹 Сложность: <b>{SAPER_DIFFS[game['diff']]['name']}</b>\n"
            f"💸 Ставка: <b>{game['bet']}</b> ₣\n"
            f"💰 Выигрыш: <b>{current_win} ₣</b> (x{game['mult']:.2f})\n\n"
            f"<i>Играем дальше или забираем?</i>"
        )
        try:
            await callback.message.edit_text(text, reply_markup=kb_saper_game(user_id), parse_mode="HTML")
        except Exception:
            pass