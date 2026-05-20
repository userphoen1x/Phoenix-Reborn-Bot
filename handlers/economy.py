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


@router.message(lambda msg: msg.text and msg.text.lower().startswith(("рулетка", "roulette")))
async def cmd_roulette(message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("❌ Формат: <code>рулетка [сумма] [красное/черное/зеро]</code>", parse_mode="HTML")
        return

    amount_str, bet_type = parts[1], parts[2].lower()
    if not amount_str.isdigit(): return
    amount = int(amount_str)

    user_id = message.from_user.id
    eco = await get_eco_data(user_id)
    if not eco or eco["balance"] < amount:
        await message.answer("❌ Недостаточно средств.")
        return

    await update_balance(user_id, -amount)
    result_num = random.randint(0, 36)
    is_red = result_num in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]

    color_name = "зеро" if result_num == 0 else ("красное" if is_red else "черное")
    color_emoji = "🟢" if result_num == 0 else ("🔴" if is_red else "⚫")

    win = 0
    if bet_type in ["зеро", "zero", "0"] and result_num == 0:
        win = amount * 35
    elif bet_type in ["красное", "red"] and is_red:
        win = amount * 2
    elif bet_type in ["черное", "black"] and not is_red and result_num != 0:
        win = amount * 2

    if win > 0:
        await update_balance(user_id, win)
        await message.answer(
            f"🎰 <b>РУЛЕТКА</b>\n\n🎡 Выпало: {color_emoji} <b>{result_num}</b> ({color_name})\n🎉 <b>ВЫИГРЫШ!</b> Вы выиграли <b>{win}</b> ₣!",
            parse_mode="HTML")
    else:
        await message.answer(
            f"🎰 <b>РУЛЕТКА</b>\n\n🎡 Выпало: {color_emoji} <b>{result_num}</b> ({color_name})\n😔 <b>ПРОИГРЫШ!</b> Ставка сгорела.",
            parse_mode="HTML")


@router.message(lambda msg: msg.text and msg.text.lower().startswith(("кости", "dice")))
async def cmd_dice(message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("❌ Формат: <code>кости [сумма] [число 1-6]</code>", parse_mode="HTML")
        return

    amount, guess = parts[1], parts[2]
    if not amount.isdigit() or not guess.isdigit(): return
    amount, guess = int(amount), int(guess)

    if guess < 1 or guess > 6: return

    user_id = message.from_user.id
    eco = await get_eco_data(user_id)
    if not eco or eco["balance"] < amount:
        await message.answer("❌ Недостаточно средств.")
        return

    await update_balance(user_id, -amount)
    dice_msg = await message.answer_dice(emoji="🎲")

    await asyncio.sleep(4)

    if dice_msg.dice.value == guess:
        win = amount * 5
        await update_balance(user_id, win)
        await message.reply(
            f"🎲 <b>КОСТИ</b>\n\n🎲 Выпало: <b>{dice_msg.dice.value}</b>\n🎉 <b>ВЫИГРЫШ!</b> Вы угадали и выиграли <b>{win}</b> ₣!",
            reply_to_message_id=dice_msg.message_id, parse_mode="HTML")
    else:
        await message.reply(
            f"🎲 <b>КОСТИ</b>\n\n🎲 Выпало: <b>{dice_msg.dice.value}</b>\n😔 <b>ПРОИГРЫШ!</b> Вы не угадали.",
            reply_to_message_id=dice_msg.message_id, parse_mode="HTML")


# --- КЛАССЫ И НАСТРОЙКИ САПЕРА ---

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


# --- ИНЛАЙН КЛАВИАТУРЫ САПЕРА ---

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


# --- ЛОГИКА ИГРЫ САПЕР ---

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

    # Списываем ставку
    await update_balance(user_id, -bet)

    # Генерация поля
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

        # Напоролся на мину
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

        # Безопасная ячейка
        game["clicked"].append(idx)
        game["mult"] += SAPER_DIFFS[game["diff"]]["mult_step"]

        # Проверка на полную победу (все безопасные открыты)
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

        # Обновляем поле
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