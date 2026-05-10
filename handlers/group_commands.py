import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

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


@router.message(F.text.lower().in_({"топ", "топ 10", "топ10", "top", "top 10", "top10"}))
async def cmd_top_trigger(message: Message):
    user_id = message.from_user.id
    target_msg_id = message.reply_to_message.message_id if message.reply_to_message else None

    await message.answer(
        "📊 <b>Выберите категорию для топа:</b>",
        reply_markup=kb_main_top(user_id),
        reply_to_message_id=target_msg_id
    )

    try:
        await message.delete()
    except Exception:
        pass


@router.callback_query(TopCb.filter())
async def process_top_callbacks(callback: CallbackQuery, callback_data: TopCb):
    if callback.from_user.id != callback_data.uid:
        await callback.answer("⚠️ Вы не можете управлять этим меню! Вызовите команду сами.", show_alert=True)
        return

    act = callback_data.act
    uid = callback_data.uid

    if act == "main":
        await callback.message.edit_text("📊 <b>Выберите категорию для топа:</b>", reply_markup=kb_main_top(uid))
    elif act == "msg":
        await callback.message.edit_text("💬 <b>Топ по сообщениям:</b>\nВыберите период:",
                                         reply_markup=kb_timeframe("msg", "main", uid))
    elif act == "cups_gain":
        await callback.message.edit_text("📈 <b>Топ поднявших кубки:</b>\nВыберите период:",
                                         reply_markup=kb_timeframe("cups_gain", "main", uid))
    elif act == "ranks":
        await callback.message.edit_text("🎖 <b>Топ по званиям:</b>", reply_markup=kb_ranks(uid))
    elif act == "wins":
        await callback.message.edit_text("⚔️ <b>Топ побед:</b>\nВыберите режим:", reply_markup=kb_wins_type(uid))
    elif act == "wins_sd":
        await callback.message.edit_text("☠️ <b>Топ побед (Столкновение):</b>\nВыберите тип:",
                                         reply_markup=kb_wins_sd(uid))
    else:
        await callback.answer()
        await callback.message.edit_text(
            f"⚙️ <b>Сбор статистики...</b>\n\n"
            f"Интерфейс готов! Команда: <code>{act}</code>.\n"
            "Осталось подключить фоновый сбор данных из Brawl Stars API.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В главное меню", callback_data=TopCb(act="main", uid=uid).pack())]
            ])
        )


@router.message()
async def message_counter(message: Message):
    if message.text:
        text_lower = message.text.lower()
        triggers = {"топ", "топ 10", "топ10", "top", "top 10", "top10"}
        if text_lower not in triggers:
            from utils.database import increment_message
            await increment_message(message.from_user.id, message.chat.id)
