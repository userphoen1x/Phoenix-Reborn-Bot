import asyncio
import re
import string
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, ChatPermissions, LinkPreviewOptions
from database.repositories.user_repo import UserRepository
from services.moderation_service import ModerationService
from utils.admin_logger import send_log
from utils.resolvers import resolve_target
from core.config import settings
from core.constants import ROLE_SYMBOLS
from tg_bot.filters.role_filters import IsModerator, IsFounder

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


def get_combined_symbols(user_id: int, game_role: str) -> str:
    syms = ""
    if str(user_id) == settings.FOUNDER_ID: syms += ROLE_SYMBOLS.get("Основатель", "👑")
    if str(user_id) in settings.DEVELOPER_IDS: syms += ROLE_SYMBOLS.get("Разработчик", "🧑🏻‍💻")
    syms += ROLE_SYMBOLS.get(game_role, "🗣️")
    return syms


def is_cmd(text: str, cmds: list) -> bool:
    if not text: return False
    t = text.lower().strip()
    for c in cmds:
        pattern = r'^' + re.escape(c) + r'(?:\s|$|[.,!?\n])'
        if re.match(pattern, t): return True
    return False


async def delete_later(message: Message, delay: int = 10800):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass


@router.message(F.text.func(lambda text: is_cmd(text, ["понизить", "демоут"])), IsFounder())
async def cmd_demote(message: Message, user_repo: UserRepository):
    target_id, target_name = await resolve_target(message, user_repo)
    if not target_id:
        sent = await message.answer("❌ Укажите @username или ответьте на сообщение пользователя.")
        return asyncio.create_task(delete_later(sent, 60))

    await user_repo.set_user_role(target_id, "Гость", "Отклонен")
    sent = await message.answer(f"⬇️ <b>{target_name}</b> понижен до Гостя и лишен системных полномочий в боте.",
                                parse_mode="HTML")
    asyncio.create_task(delete_later(sent))


@router.message(F.text.func(lambda text: is_cmd(text, ["вернуть звание", "восстановить", "вернуть"])), IsFounder())
async def cmd_restore_rank(message: Message, user_repo: UserRepository):
    target_id, target_name = await resolve_target(message, user_repo)
    if not target_id:
        sent = await message.answer("❌ Укажите @username или ответьте на сообщение пользователя.")
        return asyncio.create_task(delete_later(sent, 60))

    await user_repo.set_user_role(target_id, "Участник", "Одобрен")
    sent = await message.answer(f"✅ Полномочия <b>{target_name}</b> восстановлены.", parse_mode="HTML")
    asyncio.create_task(delete_later(sent))


@router.message(F.text.func(
    lambda text: is_cmd(text, ["мут", "mute", "анмут", "unmute", "кик", "kick", "бан", "ban", "разбан", "unban"])),
                IsModerator())
async def cmd_moderation(message: Message, bot: Bot, user_repo: UserRepository):
    if str(message.chat.id) == settings.ADMIN_CHAT_ID: return

    parts = message.text.split()
    cmd = parts[0].lower().strip(string.punctuation)

    target_id, target_name = await resolve_target(message, user_repo)
    if not target_id:
        sent_msg = await message.answer(
            "❌ Ответьте на сообщение пользователя или укажите его @username (игрок должен быть в базе).")
        return asyncio.create_task(delete_later(sent_msg, 60))

    target_username = next((word for word in parts[1:] if word.startswith("@")), None)
    clean_parts = [p for p in parts[1:] if p != target_username]

    parsed_minutes, time_str, reason = ModerationService.parse_punish_data(cmd, clean_parts)
    dt = timedelta(minutes=parsed_minutes) if parsed_minutes else None

    t_role = await user_repo.get_user_role(target_id)
    a_role = await user_repo.get_user_role(message.from_user.id)
    a_sym = get_combined_symbols(message.from_user.id, a_role)
    t_sym = get_combined_symbols(target_id, t_role)

    fmt_admin = f"{a_sym} <b>{message.from_user.first_name}</b>"
    fmt_target = f"{t_sym} <b>{target_name}</b>"

    try:
        if cmd in ["мут", "mute"]:
            await bot.restrict_chat_member(message.chat.id, target_id,
                                           permissions=ChatPermissions(can_send_messages=False),
                                           until_date=datetime.now() + dt if dt else None)
            action_pub, emoji = f"лишен права голоса на {time_str}", "🔇"
        elif cmd in ["бан", "ban"]:
            await bot.ban_chat_member(message.chat.id, target_id)
            action_pub, emoji = "забанен навсегда", "🔨"
        elif cmd in ["анмут", "unmute", "размут"]:
            await bot.restrict_chat_member(message.chat.id, target_id,
                                           permissions=ChatPermissions(can_send_messages=True, can_send_audios=True,
                                                                       can_send_documents=True, can_send_photos=True,
                                                                       can_send_videos=True, can_send_video_notes=True,
                                                                       can_send_voice_notes=True, can_send_polls=True,
                                                                       can_send_other_messages=True,
                                                                       can_add_web_page_previews=True,
                                                                       can_invite_users=True))
            action_pub, emoji = "возвращен к полноценному общению", "🔊"
        elif cmd in ["кик", "kick"]:
            await bot.ban_chat_member(message.chat.id, target_id)
            await bot.unban_chat_member(message.chat.id, target_id)
            action_pub, emoji = "исключен из группы", "👢"
        elif cmd in ["разбан", "unban"]:
            await bot.unban_chat_member(message.chat.id, target_id)
            action_pub, emoji = "разбанен (может вернуться в группу)", "✅"
        else:
            return

        try:
            await message.delete()
        except:
            pass

        pub_text = f"{emoji} Пользователь {fmt_target} был {action_pub} администратором {fmt_admin}.\n📝 Причина: {reason}"
        pub_msg = await message.answer(pub_text, link_preview_options=LinkPreviewOptions(is_disabled=True))
        asyncio.create_task(delete_later(pub_msg))

        log_payload = f"🚨 <b>ЛОГ НАКАЗАНИЯ</b>\n\n👮‍♂️ Модератор: {fmt_admin}\n👤 Нарушитель: {fmt_target}\n🛠 Действие: <b>{action_pub}</b>\n📝 Причина: {reason}"
        await send_log(bot, "TOPIC_PUNISH", log_payload)
    except Exception:
        err_msg = await message.answer("❌ Ошибка выполнения: боту не хватает прав или цель имеет иммунитет.")
        asyncio.create_task(delete_later(err_msg, 60))