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

# Глобальный словарь для ожидания ставки из меню казино
WAITING_BETS = {}


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
# 🎰 ГЛАВНОЕ МЕНЮ КАЗИНО И ИГР
# ==========================================

@router.message(F.text.lower().in_({"игра", "игры", "казик", "казино", "games", "casino"}))
async def cmd_casino(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Блэкджек", callback_data="cas_bj"),
         InlineKeyboardButton(text="💣 Сапёр", callback_data="cas_ms")],
        [InlineKeyboardButton(text="🎰 Слоты", callback_data="cas_tg_🎰"),
         InlineKeyboardButton(text="🎲 Кости", callback_data="cas_tg_🎲")],
        [InlineKeyboardButton(text="🎯 Дартс", callback_data="cas_tg_🎯"),
         InlineKeyboardButton(text="🏀 Баскетбол", callback_data="cas_tg_🏀")],
        [InlineKeyboardButton(text="⚽️ Футбол", callback_data="cas_tg_⚽"),
         InlineKeyboardButton(text="🎳 Боулинг", callback_data="cas_tg_🎳")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="cas_close")]
    ])
    await message.answer("🎰 <b>КАЗИНО PHOENIX</b>\n\nВыберите игру, чтобы испытать удачу:", reply_markup=kb,
                         parse_mode="HTML")


@router.callback_query(F.data.startswith("cas_"))
async def cb_casino_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    action = callback.data.replace("cas_", "")

    if action == "close":
        await callback.message.delete()
        if user_id in WAITING_BETS:
            del WAITING_BETS[user_id]
        return

    if action == "cancel":
        if user_id in WAITING_BETS:
            del WAITING_BETS[user_id]
        await callback.message.edit_text("❌ Ввод ставки отменен.")
        return

    if action == "ms":
        # Сапер имеет свое меню ставок, запускаем его напрямую
        from economy import kb_saper_setup_bet
        await callback.message.edit_text("💣 <b>САПЕР</b>\n\nВыберите сумму ставки (мин. 10 ₣):",
                                         reply_markup=kb_saper_setup_bet(user_id), parse_mode="HTML")
        return

    game_name = ""
    if action == "bj":
        WAITING_BETS[user_id] = {"game": "bj"}
        game_name = "🃏 Блэкджек"
    elif action.startswith("tg_"):
        emoji = action.split("_")[1]
        WAITING_BETS[user_id] = {"game": "tg", "emoji": emoji}
        game_name = f"{emoji} Игру на удачу"

    await callback.message.edit_text(
        f"Введи в чат сумму ставки для игры в <b>{game_name}</b> (или напиши 'все'):\n\n"
        f"<i>Минимальная ставка — 10 ₣</i>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cas_cancel")]]),
        parse_mode="HTML"
    )


# Универсальный фильтр для перехвата ставки в чате
class IsWaitingBetFilter:
    async def __call__(self, message: Message) -> bool:
        if not message.text: return False
        text = message.text.lower().strip()
        return message.from_user.id in WAITING_BETS and (text.isdigit() or text in ["all", "все", "всё"])


@router.message(IsWaitingBetFilter())
async def process_casino_bet(message: Message, bot: Bot):
    user_id = message.from_user.id
    state = WAITING_BETS.pop(user_id)
    bet_str = message.text.lower().strip()

    eco = await get_eco_data(user_id)
    if not eco:
        return await message.answer("❌ У вас нет счета. Зарегистрируйтесь в боте.")

    bal = eco["balance"]
    bet = bal if bet_str in ["all", "все", "всё"] else int(bet_str)

    if bet < 10:
        return await message.answer("❌ Минимальная ставка — 10 ₣.")
    if bal < bet:
        return await message.answer(f"❌ Недостаточно средств. Твой баланс: {bal} ₣.")

    # Списываем ставку сразу для всех игр кроме Сапера (он списывает внутри себя)
    await update_balance(user_id, -bet)

    if state["game"] == "bj":
        await start_blackjack(message, user_id, bet)
    elif state["game"] == "tg":
        await start_tg_game(message, user_id, bet, state["emoji"])


# ==========================================
# 🎲 ИГРЫ СО СТИКЕРАМИ TELEGRAM
# ==========================================

async def start_tg_game(message: Message, user_id: int, bet: int, emoji: str):
    # Отправляем кубик/дартс/слот
    dice_msg = await message.answer_dice(emoji=emoji)
    await asyncio.sleep(4)  # Ждем пока проиграется анимация

    val = dice_msg.dice.value
    mult = 0.0
    game_title = ""

    if emoji == "🎯":
        game_title = "ДАРТС"
        if val == 6:
            mult = 3.0  # В яблочко
        elif val in [4, 5]:
            mult = 1.5  # Близко к центру
    elif emoji == "🏀":
        game_title = "БАСКЕТБОЛ"
        if val in [4, 5]: mult = 2.0  # Попал в кольцо
    elif emoji == "⚽":
        game_title = "ФУТБОЛ"
        if val in [3, 4, 5]: mult = 1.5  # Гол
    elif emoji == "🎳":
        game_title = "БОУЛИНГ"
        if val == 6:
            mult = 3.0  # Страйк
        elif val == 5:
            mult = 1.5  # Почти страйк
    elif emoji == "🎰":
        game_title = "СЛОТЫ"
        if val == 64:
            mult = 50.0  # Три семерки
        elif val in [1, 22, 43]:
            mult = 10.0  # Три одинаковых (bar, слива, лимон)
        elif val in [44, 2, 23, 63, 21, 42]:
            mult = 2.0  # Две одинаковых
    elif emoji == "🎲":
        game_title = "КОСТИ"
        if val in [5, 6]: mult = 2.5  # Выпало 5 или 6

    if mult > 0:
        win = int(bet * mult)
        await update_balance(user_id, win)
        await message.reply(
            f"{emoji} <b>{game_title}</b>\n\n"
            f"Значение кубика: <b>{val}</b>\n"
            f"🎉 <b>ПОБЕДА!</b> Выигрыш: <b>{win}</b> ₣ (x{mult})",
            parse_mode="HTML"
        )
    else:
        await message.reply(
            f"{emoji} <b>{game_title}</b>\n\n"
            f"Значение кубика: <b>{val}</b>\n"
            f"😔 <b>ПРОИГРЫШ!</b> Потеряно: <b>{bet}</b> ₣",
            parse_mode="HTML"
        )


# ==========================================
# 🃏 БЛЭКДЖЕК (21)
# ==========================================

class BjCb(CallbackData, prefix="bj"):
    act: str


BJ_GAMES = {}


def get_card_val(c):
    v = c.split()[0]
    if v in ["J", "Q", "K"]: return 10
    if v == "A": return 11
    return int(v)


def get_hand_val(hand):
    total = sum(get_card_val(c) for c in hand)
    aces = sum(1 for c in hand if c.split()[0] == "A")
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def generate_deck():
    deck = [f"{v} {s}" for s in ["♠️", "♥️", "♦️", "♣️"] for v in
            ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]]
    random.shuffle(deck)
    return deck


def kb_bj_play(can_double=False):
    kb = [
        [InlineKeyboardButton(text="👊 Ещё", callback_data=BjCb(act="hit").pack()),
         InlineKeyboardButton(text="✋ Хватит", callback_data=BjCb(act="stand").pack())]
    ]
    bottom_row = []
    if can_double:
        bottom_row.append(InlineKeyboardButton(text="💰 Удвоить", callback_data=BjCb(act="double").pack()))
    bottom_row.append(InlineKeyboardButton(text="🏳️ Сдаться", callback_data=BjCb(act="surrender").pack()))
    kb.append(bottom_row)
    return InlineKeyboardMarkup(inline_keyboard=kb)


def render_bj_text(game, hide_dealer=True, result_msg=None):
    p_hand = " ".join(game['player'])
    p_val = get_hand_val(game['player'])

    if hide_dealer:
        d_hand = f"{game['dealer'][0]} 🂠"
        d_val = "?"
    else:
        d_hand = " ".join(game['dealer'])
        d_val = get_hand_val(game['dealer'])

    text = (
        f"🃏 <b>БЛЭКДЖЕК</b>\n\n"
        f"🏦 Дилер: {d_hand} (Очки: {d_val})\n"
        f"👤 Игрок: {p_hand} (Очки: {p_val})\n\n"
        f"💸 Ставка: <b>{game['bet']}</b> ₣"
    )
    if result_msg:
        text += f"\n\n{result_msg}"
    return text


async def start_blackjack(message: Message, user_id: int, bet: int):
    deck = generate_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    eco = await get_eco_data(user_id)
    can_double = eco["balance"] >= bet

    BJ_GAMES[user_id] = {
        "bet": bet,
        "deck": deck,
        "player": player_hand,
        "dealer": dealer_hand
    }

    p_val = get_hand_val(player_hand)
    if p_val == 21:
        await resolve_blackjack(message, user_id, "blackjack")
    else:
        await message.answer(render_bj_text(BJ_GAMES[user_id], hide_dealer=True), reply_markup=kb_bj_play(can_double),
                             parse_mode="HTML")


async def resolve_blackjack(message_or_query, user_id: int, reason: str):
    game = BJ_GAMES.pop(user_id)
    bet = game["bet"]
    p_val = get_hand_val(game["player"])

    if reason not in ["surrender", "bust", "blackjack"]:
        # Дилер добирает карты
        while get_hand_val(game["dealer"]) < 17:
            game["dealer"].append(game["deck"].pop())

    d_val = get_hand_val(game["dealer"])
    win_amount = 0
    res_msg = ""

    if reason == "surrender":
        win_amount = bet // 2
        res_msg = f"🏳️ <b>Вы сдались.</b> Возвращено: {win_amount} ₣ (Половина ставки)."
    elif reason == "bust":
        res_msg = f"💥 <b>Перебор!</b> Вы проиграли {bet} ₣."
    elif reason == "blackjack":
        win_amount = int(bet + (bet * 1.5))
        res_msg = f"🎉 <b>БЛЭКДЖЕК!</b> Выплата 3 к 2! Выигрыш: {win_amount} ₣."
    elif d_val > 21:
        win_amount = bet * 2
        res_msg = f"💥 <b>Дилер перебрал!</b> Вы выиграли {win_amount} ₣."
    elif p_val > d_val:
        win_amount = bet * 2
        res_msg = f"🎉 <b>Вы выиграли!</b> Выплата: {win_amount} ₣."
    elif p_val == d_val:
        win_amount = bet
        res_msg = f"🤝 <b>Ничья (Push).</b> Ставка {bet} ₣ возвращена."
    else:
        res_msg = f"😔 <b>Вы проиграли.</b> Дилер победил. Потеряно: {bet} ₣."

    if win_amount > 0:
        await update_balance(user_id, win_amount)

    final_text = render_bj_text(game, hide_dealer=False, result_msg=res_msg)

    if isinstance(message_or_query, CallbackQuery):
        await message_or_query.message.edit_text(final_text, parse_mode="HTML")
    else:
        await message_or_query.answer(final_text, parse_mode="HTML")


@router.callback_query(BjCb.filter())
async def cb_blackjack(callback: CallbackQuery, callback_data: BjCb):
    user_id = callback.from_user.id
    if user_id not in BJ_GAMES:
        return await callback.answer("Игра уже завершена или не ваша!", show_alert=True)

    game = BJ_GAMES[user_id]
    act = callback_data.act

    if act == "surrender":
        await resolve_blackjack(callback, user_id, "surrender")
    elif act == "stand":
        await resolve_blackjack(callback, user_id, "stand")
    elif act == "double":
        eco = await get_eco_data(user_id)
        if eco["balance"] < game["bet"]:
            return await callback.answer("Недостаточно средств для удвоения!", show_alert=True)
        # Списываем еще одну ставку
        await update_balance(user_id, -game["bet"])
        game["bet"] *= 2
        game["player"].append(game["deck"].pop())
        if get_hand_val(game["player"]) > 21:
            await resolve_blackjack(callback, user_id, "bust")
        else:
            await resolve_blackjack(callback, user_id, "stand")
    elif act == "hit":
        game["player"].append(game["deck"].pop())
        if get_hand_val(game["player"]) > 21:
            await resolve_blackjack(callback, user_id, "bust")
        else:
            # Убираем кнопку удвоения и сдачи после первой взятой карты
            await callback.message.edit_text(render_bj_text(game, hide_dealer=True),
                                             reply_markup=kb_bj_play(can_double=False), parse_mode="HTML")


# ==========================================
# 💣 САПЕР (УЖЕ БЫЛ В КОДЕ, БЕЗ ИЗМЕНЕНИЙ)
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
        [InlineKeyboardButton(text="❌ Отмена", callback_data=SaperSetupCb(act="cancel", val="0").pack())]
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
        await callback.message.edit_text("❌ Игра отменена.")
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
        await callback.message.edit_text(text, reply_markup=kb_saper_game(user_id, game_over=True), parse_mode="HTML")
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
            await callback.message.edit_text(text, reply_markup=kb_saper_game(user_id, game_over=True),
                                             parse_mode="HTML")
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
            await callback.message.edit_text(text, reply_markup=kb_saper_game(user_id, game_over=True),
                                             parse_mode="HTML")
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