import asyncio
import re
import string
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, ChatPermissions, LinkPreviewOptions
from database.repositories.user_repo import UserRepository
from utils.admin_logger import send_log
from core.config import settings
from core.constants import ROLE_SYMBOLS, TIME_UNITS_MAP, IMPLICIT_TIME_MAP
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
        if re.match(pattern, t):
            return True
    return False


async def delete_later(message: Message, delay: int = 10800):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass


@router.message(F.text.func(lambda text: is_cmd(text, ["понизить", "демоут"])), IsFounder())
async def cmd_demote(message: Message, user_repo: UserRepository):
    parts = message.text.split()
    target_id, target_name = None, None

    target_username = next((word for word in parts[1:] if word.startswith("@")), None)

    if target_username:
        all_users = await user_repo.get_all_users_for_roles()
        for u in all_users:
            tg_name = u.get("tg_name", "")
            if tg_name:
                check_name = tg_name.lower() if tg_name.startswith("@") else f"@{tg_name.lower()}"
                if check_name == target_username.lower():
                    target_id = u["user_id"]
                    target_name = target_username
                    break
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = f"@{message.reply_to_message.from_user.username}" if message.reply_to_message.from_user.username else message.reply_to_message.from_user.full_name

    if not target_id:
        sent = await message.answer("❌ Укажите @username или ответьте на сообщение пользователя.")
        asyncio.create_task(delete_later(sent, 60))
        return

    await user_repo.set_user_role(target_id, "Гость", "Отклонен")
    sent = await message.answer(f"⬇️ <b>{target_name}</b> понижен до Гостя и лишен системных полномочий в боте.",
                                parse_mode="HTML")
    asyncio.create_task(delete_later(sent))


@router.message(F.text.func(lambda text: is_cmd(text, ["вернуть звание", "восстановить", "вернуть"])), IsFounder())
async def cmd_restore_rank(message: Message, user_repo: UserRepository):
    parts = message.text.split()
    target_id, target_name = None, None

    target_username = next((word for word in parts[1:] if word.startswith("@")), None)

    if target_username:
        all_users = await user_repo.get_all_users_for_roles()
        for u in all_users:
            tg_name = u.get("tg_name", "")
            if tg_name:
                check_name = tg_name.lower() if tg_name.startswith("@") else f"@{tg_name.lower()}"
                if check_name == target_username.lower():
                    target_id = u["user_id"]
                    target_name = target_username
                    break
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = f"@{message.reply_to_message.from_user.username}" if message.reply_to_message.from_user.username else message.reply_to_message.from_user.full_name

    if not target_id:
        sent = await message.answer("❌ Укажите @username или ответьте на сообщение пользователя.")
        asyncio.create_task(delete_later(sent, 60))
        return

    await user_repo.set_user_role(target_id, "Участник", "Одобрен")
    sent = await message.answer(
        f"✅ Полномочия <b>{target_name}</b> восстановлены. Реальное звание синхронизируется в течение минуты.",
        parse_mode="HTML")
    asyncio.create_task(delete_later(sent))


@router.message(F.text.func(
    lambda text: is_cmd(text, ["мут", "mute", "анмут", "unmute", "кик", "kick", "бан", "ban", "разбан", "unban"])),
                IsModerator())
async def cmd_moderation(message: Message, bot: Bot, user_repo: UserRepository):
    if str(message.chat.id) == settings.ADMIN_CHAT_ID: return

    parts = message.text.split()
    cmd = parts[0].lower().strip(string.punctuation)

    target_id = None
    target_name = None

    target_username = next((word for word in parts[1:] if word.startswith("@")), None)

    if target_username:
        all_users = await user_repo.get_all_users_for_roles()
        for u in all_users:
            tg_name = u.get("tg_name", "")
            if tg_name:
                check_name = tg_name.lower() if tg_name.startswith("@") else f"@{tg_name.lower()}"
                if check_name == target_username.lower():
                    target_id = u["user_id"]
                    target_name = target_username
                    break
        if not target_id:
            sent_msg = await message.answer(f"❌ Пользователь {target_username} не найден в базе.")
            asyncio.create_task(delete_later(sent_msg, 60))
            return
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        u = message.reply_to_message.from_user
        target_name = f"@{u.username}" if u.username else u.full_name
    else:
        sent_msg = await message.answer("❌ Ответьте на сообщение пользователя или укажите его @username.")
        asyncio.create_task(delete_later(sent_msg, 60))
        return

    clean_parts = [p for p in parts[1:] if p != target_username]

    parsed_minutes = None
    time_str = "10 минут"
    reason_parts = []

    if cmd in ["бан", "ban"]:
        parsed_minutes = 0
        time_str = "навсегда"
        reason_parts = clean_parts
    elif cmd in ["мут", "mute"] and clean_parts:
        first_word = clean_parts[0].lower()
        if first_word in IMPLICIT_TIME_MAP:
            parsed_minutes = IMPLICIT_TIME_MAP[first_word]
            reason_parts = clean_parts[1:]
        elif any(first_word.endswith(s) and first_word[:-len(s)].isdigit() for s in TIME_UNITS_MAP.keys()):
            for suffix, multiplier in sorted(TIME_UNITS_MAP.items(), key=lambda x: len(x[0]), reverse=True):
                if first_word.endswith(suffix):
                    val_str = first_word[:-len(suffix)]
                    if val_str.isdigit():
                        parsed_minutes = int(val_str) * multiplier
                        reason_parts = clean_parts[1:]
                        break
        elif first_word.isdigit():
            val = int(first_word)
            if len(clean_parts) > 1:
                second_word = clean_parts[1].lower()
                matched_multiplier = None
                for suffix, multiplier in sorted(TIME_UNITS_MAP.items(), key=lambda x: len(x[0]), reverse=True):
                    if second_word == suffix or second_word.startswith(suffix):
                        matched_multiplier = multiplier
                        break
                if matched_multiplier:
                    parsed_minutes = val * matched_multiplier
                    reason_parts = clean_parts[2:]
                else:
                    parsed_minutes = val
                    reason_parts = clean_parts[1:]
            else:
                parsed_minutes = val
                reason_parts = clean_parts[1:]
        else:
            reason_parts = clean_parts

    if cmd in ["мут", "mute"] and parsed_minutes is None:
        parsed_minutes = 10

    dt = None
    if parsed_minutes == 0:
        time_str = "навсегда"
    elif parsed_minutes is not None:
        dt = timedelta(minutes=parsed_minutes)
        if parsed_minutes < 60:
            m = parsed_minutes
            if m % 10 == 1 and m % 100 != 11:
                time_str = f"{m} минуту"
            elif 2 <= m % 10 <= 4 and not (12 <= m % 100 <= 14):
                time_str = f"{m} минуты"
            else:
                time_str = f"{m} минут"
        elif parsed_minutes < 1440:
            h = parsed_minutes // 60
            if h % 10 == 1 and h % 100 != 11:
                time_str = f"{h} час"
            elif 2 <= h % 10 <= 4 and not (12 <= h % 100 <= 14):
                time_str = f"{h} часа"
            else:
                time_str = f"{h} часов"
        else:
            d = parsed_minutes // 1440
            if d % 10 == 1 and d % 100 != 11:
                time_str = f"{d} день"
            elif 2 <= d % 10 <= 4 and not (12 <= d % 100 <= 14):
                time_str = f"{d} дня"
            else:
                time_str = f"{d} дней"

    reason = " ".join(reason_parts) if reason_parts else "Не указана"

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
            action_pub = f"лишен права голоса на {time_str}"
            emoji = "🔇"
        elif cmd in ["бан", "ban"]:
            await bot.ban_chat_member(message.chat.id, target_id)
            action_pub = f"забанен навсегда"
            emoji = "🔨"
        elif cmd in ["анмут", "unmute", "размут"]:
            await bot.restrict_chat_member(message.chat.id, target_id,
                                           permissions=ChatPermissions(can_send_messages=True, can_send_audios=True,
                                                                       can_send_documents=True, can_send_photos=True,
                                                                       can_send_videos=True, can_send_video_notes=True,
                                                                       can_send_voice_notes=True, can_send_polls=True,
                                                                       can_send_other_messages=True,
                                                                       can_add_web_page_previews=True,
                                                                       can_invite_users=True))
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