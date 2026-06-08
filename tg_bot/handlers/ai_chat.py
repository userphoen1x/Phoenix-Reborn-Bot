import re
import random
import logging
import asyncio
import os
import base64
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from dishka import inject
from dishka.integrations.aiogram import FromDishka

from services.ai_service import AiService
from database.repositories.chat_repo import ChatRepository
from database.repositories.user_repo import UserRepository
from database.repositories.economy_repo import EconomyRepository
from core.config import settings

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), lambda msg: str(msg.chat.id) != os.getenv("ADMIN_CHAT_ID"))

VOICE_REPLY_CHANCE = 0.01

class AiModeCb(CallbackData, prefix="aimode"):
    mode: str
    uid: int

SCRIPTED_PREFIXES = ("❌", "✅", "⚠️", "🎭", "📊", "🏆", "🎰", "🎲", "🎯", "🎳", "⚽", "🏀", "💣", "🃏", "💰", "💳", "⏳", "⬇️", "🔇", "🔊", "👢", "🔨", "💬", "🔥", "📈", "⚔️", "🌵", "👥", "👤", "🎖")

async def _send_ai_reply(message: Message, bot: Bot, ai_response: str, ai_service: AiService):
    if random.random() < VOICE_REPLY_CHANCE:
        try:
            voice_bytes = await ai_service.generate_voice(ai_response)
            if voice_bytes:
                await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
                await message.reply_voice(BufferedInputFile(voice_bytes, filename="voice.wav"))
                return
        except Exception: pass
    await message.reply(ai_response, parse_mode=None)

async def _process_media_message(message: Message, bot: Bot, ai_service: AiService) -> tuple[str | None, str, str]:
    if message.voice:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        file = await bot.get_file(message.voice.file_id)
        file_bytes = await bot.download_file(file.file_path)
        transcript = await ai_service.transcribe_audio(file_bytes.read(), "voice.ogg")
        if transcript: return transcript, "voice", ""
        return None, "", ""
    if message.video_note:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        file = await bot.get_file(message.video_note.file_id)
        file_bytes = await bot.download_file(file.file_path)
        transcript = await ai_service.transcribe_audio(file_bytes.read(), "video_note.mp4")
        if transcript: return transcript, "video_note", ""
        return None, "", ""
    if message.video:
        if message.video.file_size and message.video.file_size > 20 * 1024 * 1024: return None, "", ""
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        file = await bot.get_file(message.video.file_id)
        file_bytes = await bot.download_file(file.file_path)
        transcript = await ai_service.transcribe_audio(file_bytes.read(), "video.mp4")
        if transcript: return transcript, "video", ""
        return None, "", ""
    if message.photo:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        img_b64 = base64.b64encode(file_bytes.read()).decode("utf-8")
        caption = message.caption or ""
        return img_b64, "photo", caption
    return None, "", ""

@router.message(Command("характер"))
@inject
async def cmd_change_ai_mode(message: Message, user_repo: FromDishka[UserRepository]):
    user_id = message.from_user.id
    role = await user_repo.get_user_role(user_id)
    is_tech = str(user_id) == settings.FOUNDER_ID or str(user_id) in settings.DEVELOPER_IDS
    if not is_tech and role not in ["Президент", "Вице-президент"]: return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦅 Классический Феникс", callback_data=AiModeCb(mode="default", uid=user_id).pack())],
        [InlineKeyboardButton(text="📜 Мудрый Философ", callback_data=AiModeCb(mode="philosopher", uid=user_id).pack())]
    ])
    await message.answer("🎭 <b>Настройка искусственного интеллекта</b>\n\nВыбери характер:", reply_markup=kb, parse_mode="HTML")

@router.callback_query(AiModeCb.filter())
@inject
async def cb_set_ai_mode(callback: CallbackQuery, callback_data: AiModeCb, user_repo: FromDishka[UserRepository], chat_repo: FromDishka[ChatRepository]):
    if callback.from_user.id != callback_data.uid: return await callback.answer("❌ Это не твое меню настроек!", show_alert=True)
    user_id = callback.from_user.id
    role = await user_repo.get_user_role(user_id)
    is_tech = str(user_id) == settings.FOUNDER_ID or str(user_id) in settings.DEVELOPER_IDS

    if not is_tech and role not in ["Президент", "Вице-президент"]:
        return await callback.answer("❌ Недостаточно прав!", show_alert=True)

    mode = callback_data.mode
    await chat_repo.set_chat_mode(callback.message.chat.id, mode)
    await chat_repo.clear_chat_logs(callback.message.chat.id)
    mode_names = {"default": "🦅 Классический Феникс", "philosopher": "📜 Мудрый Философ"}
    await callback.message.edit_text(f"✅ Character Mode успешно изменен на: <b>{mode_names.get(mode, 'Классический')}</b>", parse_mode="HTML")
    await callback.answer()

@router.message(Command("clear_ai"))
@inject
async def cmd_clear_ai_memory(message: Message, user_repo: FromDishka[UserRepository], chat_repo: FromDishka[ChatRepository]):
    user_id = message.from_user.id
    role = await user_repo.get_user_role(user_id)
    is_tech = str(user_id) == settings.FOUNDER_ID or str(user_id) in settings.DEVELOPER_IDS
    if not is_tech and role not in ["Президент", "Вице-президент"]: return

    await chat_repo.clear_chat_logs(message.chat.id)
    await message.answer("🧹 <b>Память ИИ успешно очищена!</b>\nФеникс забыл контекст последних сообщений в этом чате.", parse_mode="HTML")

@router.message()
@inject
async def universal_chat_handler(message: Message, bot: Bot, chat_repo: FromDishka[ChatRepository], eco_repo: FromDishka[EconomyRepository], ai_service: FromDishka[AiService]):
    if message.from_user.is_bot: return
    user_id = message.from_user.id
    user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    has_text = bool(message.text)
    has_media = bool(message.voice or message.video_note or message.video or message.photo)
    if not has_text and not has_media: return
    message_text = message.text or message.caption or ""

    if has_text:
        await asyncio.gather(chat_repo.increment_message(user_id, message.chat.id, user_name),
                             chat_repo.log_chat_message(message.chat.id, user_id, user_name, message_text),
                             return_exceptions=True)
        text_lower = message_text.lower().strip()
        ignore_list = ["топ", "top", "топ10", "мут", "mute", "анмут", "unmute", "размут", "кик", "kick", "бан", "ban",
                       "разбан", "unban", "слоты", "слот", "кости", "кубик", "dice", "дартс", "darts", "боулинг",
                       "боул", "футбол", "баскетбол", "сапер", "saper", "блекджек", "21", "очко", "баланс", "работа",
                       "ворк", "перевод"]
        if any(text_lower.startswith(cmd) or text_lower.startswith("/" + cmd) for cmd in ignore_list): return

    bot_info = await bot.get_me()
    text_lower = message_text.lower().strip()
    is_mentioned = f"@{bot_info.username.lower()}" in text_lower or bot_info.first_name.lower() in text_lower
    is_reply_to_bot = bool(message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id)

    if is_reply_to_bot and message.reply_to_message.text:
        if any(message.reply_to_message.text.startswith(prefix) for prefix in SCRIPTED_PREFIXES): return

    random_interject = random.random() < 0.01 if has_text else False
    should_respond = is_mentioned or is_reply_to_bot or random_interject
    if has_media and not (is_mentioned or is_reply_to_bot): return
    if not should_respond and not has_media: return

    eco = await eco_repo.get_eco_data(user_id)
    if not eco or not eco.get("bs_tag"):
        if is_mentioned or is_reply_to_bot: await message.reply("❌ Я общаюсь только с верифицированными участниками клуба. Отправь мне свой тег в ЛС!")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    history = await chat_repo.get_chat_context(message.chat.id, limit=10)

    media_payload = None
    if has_media:
        data, m_type, caption = await _process_media_message(message, bot, ai_service)
        if not data:
            await message.reply("не смог обработать, попробуй ещё раз", parse_mode=None)
            return
        media_payload = (data, m_type, caption)

    ai_response = await ai_service.generate_response(message.chat.id, user_name, message_text, bot_info.id, history, media_payload)
    await _send_ai_reply(message, bot, ai_response, ai_service)

    try: await chat_repo.log_chat_message(message.chat.id, bot_info.id, bot_info.first_name, ai_response)
    except Exception: pass