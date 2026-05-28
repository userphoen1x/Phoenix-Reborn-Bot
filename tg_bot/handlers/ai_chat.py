import random
import asyncio
import os
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from services.ai_service import AiService
from database.repositories.chat_repo import ChatRepository
from database.repositories.user_repo import UserRepository
from database.repositories.economy_repo import EconomyRepository

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), lambda msg: str(msg.chat.id) != os.getenv("ADMIN_CHAT_ID"))

class AiModeCb(CallbackData, prefix="aimode"):
    mode: str
    uid: int

SCRIPTED_PREFIXES = ("❌", "✅", "⚠️", "🎭", "📊", "🏆", "🎰", "🎲", "🎯", "🎳", "⚽", "🏀", "💣", "🃏", "💰", "💳", "⏳", "⬇️", "🔇", "🔊", "👢", "🔨", "💬", "🔥", "📈", "⚔️", "🌵", "👥", "👤", "🎖")

@router.message(Command("характер"))
async def cmd_change_ai_mode(message: Message, user_repo: UserRepository):
    role = await user_repo.get_user_role(message.from_user.id)
    if role not in ["Основатель", "Программист", "Президент", "Вице-президент"]: return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🦅 Классический Феникс", callback_data=AiModeCb(mode="default", uid=message.from_user.id).pack())], [InlineKeyboardButton(text="☣️ Токсичный Геймер", callback_data=AiModeCb(mode="toxic", uid=message.from_user.id).pack())], [InlineKeyboardButton(text="📜 Мудрый Философ", callback_data=AiModeCb(mode="philosopher", uid=message.from_user.id).pack())]])
    await message.answer("🎭 <b>Настройка искусственного интеллекта</b>\n\nВыбери характер:", reply_markup=kb, parse_mode="HTML")

@router.callback_query(AiModeCb.filter())
async def cb_set_ai_mode(callback: CallbackQuery, callback_data: AiModeCb, chat_repo: ChatRepository):
    if callback.from_user.id != callback_data.uid: return await callback.answer("❌ Это не твое меню настроек!", show_alert=True)
    await chat_repo.set_chat_mode(callback.message.chat.id, callback_data.mode)
    await chat_repo.clear_chat_logs(callback.message.chat.id)
    mode_names = {"default": "🦅 Классический Феникс", "toxic": "☣️ Токсичный Геймер", "philosopher": "📜 Мудрый Философ"}
    await callback.message.edit_text(f"✅ Character Mode изменен на: <b>{mode_names[callback_data.mode]}</b>", parse_mode="HTML")
    await callback.answer()

@router.message()
async def universal_chat_handler(message: Message, bot: Bot, chat_repo: ChatRepository, eco_repo: EconomyRepository, ai_service: AiService):
    if not message.text or message.from_user.is_bot: return
    user_id = message.from_user.id
    user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    text_lower = message.text.lower().strip()
    await asyncio.gather(chat_repo.increment_message(user_id, message.chat.id, user_name), chat_repo.log_chat_message(message.chat.id, user_id, user_name, message.text), return_exceptions=True)
    ignore_list = ["топ", "top", "топ10", "мут", "mute", "анмут", "unmute", "размут", "кик", "kick", "бан", "ban", "разбан", "unban", "слоты", "слот", "кости", "кубик", "dice", "дартс", "darts", "боулинг", "боул", "футбол", "баскетбол", "сапер", "saper", "блекджек", "21", "очко", "баланс", "работа", "ворк", "перевод"]
    if any(text_lower.startswith(cmd) or text_lower.startswith("/" + cmd) for cmd in ignore_list): return
    bot_info = await bot.get_me()
    is_mentioned = f"@{bot_info.username.lower()}" in text_lower or bot_info.first_name.lower() in text_lower
    is_reply_to_bot = bool(message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id)
    if is_reply_to_bot and message.reply_to_message.text:
        if any(message.reply_to_message.text.startswith(prefix) for prefix in SCRIPTED_PREFIXES): return
    if is_mentioned or is_reply_to_bot or random.random() < 0.01:
        eco = await eco_repo.get_eco_data(user_id)
        if not eco or not eco.get("bs_tag"):
            if is_mentioned or is_reply_to_bot: await message.reply("❌ Я общаюсь только с верифицированными участниками клуба.")
            return
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        history = await chat_repo.get_chat_context(message.chat.id, limit=10)
        ai_response = await ai_service.generate_response(message.chat.id, user_name, message.text, bot_info.id, history)
        await message.reply(ai_response, parse_mode=None)
        await chat_repo.log_chat_message(message.chat.id, bot_info.id, bot_info.first_name, ai_response)