import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


def kb_main_top():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 По сообщениям", callback_data="top_msg")],
        [InlineKeyboardButton(text="📈 Поднявшие кубки", callback_data="top_cups_gain")],
        [InlineKeyboardButton(text="🏆 Общие кубки", callback_data="top_cups_total")],
        [InlineKeyboardButton(text="🎖 Звания (Ранговые)", callback_data="top_ranks")],
        [InlineKeyboardButton(text="⚔️ Выигранные игры", callback_data="top_wins")]
    ])


def kb_timeframe(prefix: str, back_cb: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="За день", callback_data=f"{prefix}_day"),
         InlineKeyboardButton(text="За неделю", callback_data=f"{prefix}_week")],
        [InlineKeyboardButton(text="За месяц", callback_data=f"{prefix}_month"),
         InlineKeyboardButton(text="За всё время", callback_data=f"{prefix}_all")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)]
    ])


def kb_ranks():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Актуальные", callback_data="top_ranks_current")],
        [InlineKeyboardButton(text="Рекордные", callback_data="top_ranks_highest")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="top_main")]
    ])


def kb_wins_type():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В сумме", callback_data="top_wins_total")],
        [InlineKeyboardButton(text="3 на 3", callback_data="top_wins_3v3")],
        [InlineKeyboardButton(text="Столкновение", callback_data="top_wins_sd")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="top_main")]
    ])


def kb_wins_sd():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В сумме", callback_data="top_wins_sd_total")],
        [InlineKeyboardButton(text="Одиночное", callback_data="top_wins_sd_solo")],
        [InlineKeyboardButton(text="Дуо", callback_data="top_wins_sd_duo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="top_wins")]
    ])


@router.message(F.text.lower().in_({"топ", "топ 10", "топ10", "top", "top 10", "top10"}))
async def cmd_top_trigger(message: Message):
    target = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id

    await message.answer("📊 <b>Выберите категорию для топа:</b>", reply_markup=kb_main_top())

    try:
        await message.delete()
    except Exception:
        pass


@router.callback_query(F.data == "top_main")
async def cb_top_main(callback: CallbackQuery):
    await callback.message.edit_text("📊 <b>Выберите категорию для топа:</b>", reply_markup=kb_main_top())


@router.callback_query(F.data == "top_msg")
async def cb_top_msg(callback: CallbackQuery):
    await callback.message.edit_text("💬 <b>Топ по сообщениям:</b>\nВыберите период:",
                                     reply_markup=kb_timeframe("top_msg", "top_main"))


@router.callback_query(F.data == "top_cups_gain")
async def cb_top_cups_gain(callback: CallbackQuery):
    await callback.message.edit_text("📈 <b>Топ поднявших кубки:</b>\nВыберите период:",
                                     reply_markup=kb_timeframe("top_cups_gain", "top_main"))


@router.callback_query(F.data == "top_ranks")
async def cb_top_ranks(callback: CallbackQuery):
    await callback.message.edit_text("🎖 <b>Топ по званиям:</b>", reply_markup=kb_ranks())


@router.callback_query(F.data == "top_wins")
async def cb_top_wins(callback: CallbackQuery):
    await callback.message.edit_text("⚔️ <b>Топ побед:</b>\nВыберите режим:", reply_markup=kb_wins_type())


@router.callback_query(F.data == "top_wins_sd")
async def cb_top_wins_sd(callback: CallbackQuery):
    await callback.message.edit_text("☠️ <b>Топ побед (Столкновение):</b>\nВыберите тип:", reply_markup=kb_wins_sd())


@router.message()
async def message_counter(message: Message):
    if message.text:
        text_lower = message.text.lower()
        triggers = {"топ", "топ 10", "топ10", "top", "top 10", "top10"}
        if text_lower not in triggers:
            from utils.database import increment_message
            await increment_message(message.from_user.id, message.chat.id)