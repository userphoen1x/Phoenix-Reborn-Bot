import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from utils.database import get_top_messages, get_top_gain, get_top_absolute
from utils.brawl_api import get_all_club_members

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

class TopCb(CallbackData, prefix="top"):
    act: str
    uid: int

def kb_main_top(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 По сообщениям", callback_data=TopCb(act="msg", uid=uid).pack())],
        [InlineKeyboardButton(text="📈 Поднявшие кубки", callback_data=TopCb(act="cups_gain", uid=uid).pack())],
        [InlineKeyboardButton(text="🏆 Общие кубки", callback_data=TopCb(act="cups_total", uid=uid).pack())],
        [InlineKeyboardButton(text="🎖 Звания (Ранговые)", callback_data=TopCb(act="ranks", uid=uid).pack())],
        [InlineKeyboardButton(text="⚔️ Выигранные игры", callback_data=TopCb(act="wins", uid=uid).pack())]
    ])

def kb_timeframe(prefix: str, back_cb: str, uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="За день", callback_data=TopCb(act=f"{prefix}_day", uid=uid).pack()),
         InlineKeyboardButton(text="За неделю", callback_data=TopCb(act=f"{prefix}_week", uid=uid).pack())],
        [InlineKeyboardButton(text="За месяц", callback_data=TopCb(act=f"{prefix}_month", uid=uid).pack()),
         InlineKeyboardButton(text="За всё время", callback_data=TopCb(act=f"{prefix}_all", uid=uid).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act=back_cb, uid=uid).pack())]
    ])

def kb_ranks(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Актуальные", callback_data=TopCb(act="ranks_curr", uid=uid).pack())],
        [InlineKeyboardButton(text="Рекордные", callback_data=TopCb(act="ranks_high", uid=uid).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="main", uid=uid).pack())]
    ])

def kb_wins_type(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В сумме", callback_data=TopCb(act="wins_tot", uid=uid).pack())],
        [InlineKeyboardButton(text="3 на 3", callback_data=TopCb(act="wins_3v3", uid=uid).pack())],
        [InlineKeyboardButton(text="Столкновение", callback_data=TopCb(act="wins_sd", uid=uid).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="main", uid=uid).pack())]
    ])

def kb_wins_sd(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В сумме", callback_data=TopCb(act="wins_sd_tot", uid=uid).pack())],
        [InlineKeyboardButton(text="Одиночное", callback_data=TopCb(act="wins_sd_solo", uid=uid).pack())],
        [InlineKeyboardButton(text="Дуо", callback_data=TopCb(act="wins_sd_duo", uid=uid).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="wins", uid=uid).pack())]
    ])

# --- АДМИНСКАЯ КОМАНДА ДЛЯ МОМЕНТАЛЬНОГО СБОРА БАЗЫ ---
@router.message(Command("force_scan"))
async def admin_force_scan(message: Message):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or message.from_user.id != int(admin_id):
        return
    await message.answer("🔄 Запускаю принудительный сбор статистики по всем кланам. Это займет около 10-15 секунд...")
    from utils.scheduler import collect_daily_stats
    await collect_daily_stats()
    await message.answer("✅ Сбор статистики завершен! База данных заполнена свежей информацией.")

@router.message(F.text.lower().in_({"топ", "топ 10", "топ10", "top", "top 10", "top10"}))
async def cmd_top_trigger(message: Message):
    user_id = message.from_user.id
    target_msg_id = message.reply_to_message.message_id if message.reply_to_message else None
    await message.answer("📊 <b>Выберите категорию для топа:</b>", reply_markup=kb_main_top(user_id), reply_to_message_id=target_msg_id)
    try:
        await message.delete()
    except Exception:
        pass

@router.callback_query(TopCb.filter())
async def process_top_callbacks(callback: CallbackQuery, callback_data: TopCb):
    if callback.from_user.id != callback_data.uid:
        await callback.answer("⚠️ Вы не можете управлять этим меню!", show_alert=True)
        return

    act = callback_data.act
    uid = callback_data.uid

    # Навигация по меню
    if act == "main":
        await callback.message.edit_text("📊 <b>Выберите категорию для топа:</b>", reply_markup=kb_main_top(uid))
        return
    elif act == "msg":
        await callback.message.edit_text("💬 <b>Топ по сообщениям:</b>\nВыберите период:", reply_markup=kb_timeframe("msg", "main", uid))
        return
    elif act == "cups_gain":
        await callback.message.edit_text("📈 <b>Топ поднявших кубки:</b>\nВыберите период:", reply_markup=kb_timeframe("cups_gain", "main", uid))
        return
    elif act == "ranks":
        await callback.message.edit_text("🎖 <b>Топ по званиям:</b>", reply_markup=kb_ranks(uid))
        return
    elif act == "wins":
        await callback.message.edit_text("⚔️ <b>Топ побед:</b>\nВыберите режим:", reply_markup=kb_wins_type(uid))
        return
    elif act == "wins_sd":
        await callback.message.edit_text("☠️ <b>Топ побед (Столкновение):</b>\nВыберите тип:", reply_markup=kb_wins_sd(uid))
        return

    # Логика сбора данных
    await callback.message.edit_text("⏳ <b>Вычисляю...</b>")
    kb_back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В главное меню", callback_data=TopCb(act="main", uid=uid).pack())]])

    def format_top(title, data, suffix=""):
        if not data:
            return f"📊 <b>{title}</b>\n\nНет данных. Возможно, нужно обновить базу."
        text = f"📊 <b>{title}</b>\n\n"
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i, (name, val) in enumerate(data[:10]):
            text += f"{medals[i]} <b>{name}</b> — {val} {suffix}\n"
        return text

    try:
        if act.startswith("msg_"):
            days = {"msg_day": 1, "msg_week": 7, "msg_month": 30, "msg_all": None}.get(act)
            titles = {1: "Топ сообщений (Сутки)", 7: "Топ сообщений (Неделя)", 30: "Топ сообщений (Месяц)", None: "Топ сообщений (Всё время)"}
            data = await get_top_messages(days)
            await callback.message.edit_text(format_top(titles[days], data, "сообщ."), reply_markup=kb_back)

        elif act.startswith("cups_gain_"):
            days = {"cups_gain_day": 1, "cups_gain_week": 7, "cups_gain_month": 30, "cups_gain_all": 3650}.get(act)
            titles = {1: "Подняли кубков (Сутки)", 7: "Подняли кубков (Неделя)", 30: "Подняли кубков (Месяц)", 3650: "Подняли кубков (Всё время)"}
            data = await get_top_gain("trophies", days)
            await callback.message.edit_text(format_top(titles[days], data, "🏆"), reply_markup=kb_back)

        elif act == "cups_total":
            members = await get_all_club_members()
            members.sort(key=lambda x: x.get("trophies", 0), reverse=True)
            data = [(m["name"], m.get("trophies", 0)) for m in members[:10]]
            await callback.message.edit_text(format_top("Топ 10 по Общим Кубкам (LIVE)", data, "🏆"), reply_markup=kb_back)

        elif act.startswith("ranks_"):
            col = "rank_current" if act == "ranks_curr" else "rank_highest"
            title = "Актуальные звания" if act == "ranks_curr" else "Рекордные звания"
            data = await get_top_absolute(col)
            await callback.message.edit_text(format_top(title, data, "🎖"), reply_markup=kb_back)

        elif act.startswith("wins_"):
            col_map = {
                "wins_tot": ("solo_wins + duo_wins + wins_3v3", "Всего побед"),
                "wins_3v3": ("wins_3v3", "Победы 3 на 3"),
                "wins_sd_tot": ("solo_wins + duo_wins", "Победы Столкновение (Все)"),
                "wins_sd_solo": ("solo_wins", "Победы Соло"),
                "wins_sd_duo": ("duo_wins", "Победы Дуо")
            }
            col, title = col_map[act]
            data = await get_top_absolute(col)
            await callback.message.edit_text(format_top(title, data, "⚔️"), reply_markup=kb_back)

    except Exception:
        await callback.message.edit_text("❌ Произошла ошибка при расчетах.", reply_markup=kb_back)

@router.message()
async def message_counter(message: Message):
    if message.text:
        if message.text.lower() not in {"топ", "топ 10", "топ10", "top", "top 10", "top10"}:
            from utils.database import increment_message
            await increment_message(message.from_user.id, message.chat.id)