import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, ChatPermissions, LinkPreviewOptions
from aiogram.filters import Command
from database.repositories.user_repo import UserRepository
from utils.admin_logger import send_log
from core.config import settings

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

ROLE_SYMBOLS = {"Основатель": "👑", "Программист": "👨‍💻", "Президент": "🌟", "Вице-президент": "⭐", "Ветеран": "🎖", "Участник": "👤", "Гость": "👻"}

async def delete_later(message: Message, delay: int = 10800):
    await asyncio.sleep(delay)
    try: await message.delete()
    except: pass

@router.message(Command("id"))
async def cmd_get_topic_id(message: Message):
    if message.message_thread_id: await message.answer(f"ID этого топика: <code>{message.message_thread_id}</code>", parse_mode="HTML")
    else: await message.answer(f"ID этого чата: <code>{message.chat.id}</code>", parse_mode="HTML")

@router.message(Command("force_scan"))
async def admin_force_scan(message: Message):
    if str(message.from_user.id) != settings.ADMIN_ID: return
    sent_msg = await message.answer("⏳ Собираю данные...")
    from scheduler.jobs import collect_daily_stats
    await collect_daily_stats()
    await sent_msg.edit_text("✅ Готово")
    asyncio.create_task(delete_later(sent_msg, 60))

@router.message(Command("all_reg_list"))
async def cmd_all_reg_list(message: Message, user_repo: UserRepository):
    admin_role = await user_repo.get_user_role(message.from_user.id)
    if admin_role not in ["Основатель", "Программист", "Президент", "Вице-президент"]: return
    users = await user_repo.get_all_registered_users()
    if not users:
        sent = await message.answer("📭 Список зарегистрированных пользователей пуст.")
        asyncio.create_task(delete_later(sent, 60))
        return
    lines = ["📋 <b>Список зарегистрированных игроков:</b>\n"]
    for i, (tg_name, tag, player_name) in enumerate(users, 1):
        name_str = tg_name if tg_name.startswith("@") else f"<b>{tg_name}</b>"
        lines.append(f"{i}. {name_str} привязан к тегу {tag} ({player_name})")
    text = "\n".join(lines)
    for x in range(0, len(text), 4000):
        sent = await message.answer(text[x:x + 4000], parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True))
        asyncio.create_task(delete_later(sent, 10800))
    try: await message.delete()
    except: pass

@router.message(F.text.lower().startswith(("мут", "mute", "анмут", "unmute", "кик", "kick", "бан", "ban", "разбан", "unban")))
async def cmd_moderation(message: Message, bot: Bot, user_repo: UserRepository):
    if str(message.chat.id) == settings.ADMIN_CHAT_ID: return
    a_role = await user_repo.get_user_role(message.from_user.id)
    if a_role not in ["Основатель", "Программист", "Президент", "Вице-президент"]: return
    parts = message.text.split()
    cmd = parts[0].lower()
    target_id, target_name = None, None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        u = message.reply_to_message.from_user
        target_name = f"@{u.username}" if u.username else u.full_name
    if not target_id:
        sent_msg = await message.answer("❌ Ответьте на сообщение пользователя.")
        asyncio.create_task(delete_later(sent_msg, 60))
        return
    dt = timedelta(minutes=10)
    time_str = "10 минут"
    if cmd in ["бан", "ban"]: dt = None; time_str = "навсегда"
    reason = " ".join(parts[1:]) if len(parts) > 1 else "Не указана"
    t_role = await user_repo.get_user_role(target_id)
    fmt_admin = f"{ROLE_SYMBOLS.get(a_role, '👻')} <b>{message.from_user.first_name}</b>"
    fmt_target = f"{ROLE_SYMBOLS.get(t_role, '👻')} <b>{target_name}</b>"
    try:
        if cmd in ["мут", "mute"]:
            await bot.restrict_chat_member(message.chat.id, target_id, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now() + dt)
            action_pub = f"лишен права голоса на {time_str}"
            emoji = "🔇"
        elif cmd in ["бан", "ban"]:
            await bot.ban_chat_member(message.chat.id, target_id)
            action_pub = f"забанен навсегда"
            emoji = "🔨"
        elif cmd in ["анмут", "unmute", "размут"]:
            await bot.restrict_chat_member(message.chat.id, target_id, permissions=ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True, can_invite_users=True))
            action_pub = "возвращен к полноценному общению"
            emoji = "🔊"
        elif cmd in ["кик", "kick"]:
            await bot.ban_chat_member(message.chat.id, target_id)
            await bot.unban_chat_member(message.chat.id, target_id)
            action_pub = "исключен из группы"
            emoji = "👢"
        elif cmd in ["разбан", "unban"]:
            await bot.unban_chat_member(message.chat.id, target_id)
            action_pub = "разбанен (может вернуться в группу)"
            emoji = "✅"
        else: return
        try: await message.delete()
        except: pass
        pub_text = f"{emoji} Пользователь {fmt_target} был {action_pub} администратором {fmt_admin}.\n📝 Причина: {reason}"
        pub_msg = await message.answer(pub_text, link_preview_options=LinkPreviewOptions(is_disabled=True))
        asyncio.create_task(delete_later(pub_msg))
        log_payload = f"🚨 <b>ЛОГ НАКАЗАНИЯ</b>\n\n👮‍♂️ Модератор: {fmt_admin}\n👤 Нарушитель: {fmt_target}\n🛠 Действие: <b>{action_pub}</b>\n📝 Причина: {reason}"
        await send_log(bot, "TOPIC_PUNISH", log_payload)
    except Exception:
        err_msg = await message.answer("❌ Ошибка выполнения: боту не хватает прав или цель имеет иммунитет.")
        asyncio.create_task(delete_later(err_msg, 60))