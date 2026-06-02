import asyncio
import re
import string
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, ChatPermissions, LinkPreviewOptions
from aiogram.filters import Command
from database.repositories.user_repo import UserRepository
from utils.admin_logger import send_log
from core.config import settings

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

ROLE_SYMBOLS = {"Главарь": "👑", "Программист": "🧑🏻‍💻", "Президент": "🌟", "Вице-президент": "⭐", "Ветеран": "🎖",
                "Участник": "👤", "Гость": "🗣️"}


def get_combined_symbols(user_id: int, game_role: str) -> str:
    syms = ""
    if str(user_id) == settings.FOUNDER_ID: syms += ROLE_SYMBOLS.get("Главарь", "👑")
    if str(user_id) in settings.DEVELOPER_IDS: syms += ROLE_SYMBOLS.get("Программист", "🧑🏻‍💻")
    syms += ROLE_SYMBOLS.get(game_role, "🗣️")
    return syms


def is_cmd(text: str, cmds: list) -> bool:
    if not text: return False
    t = text.lower().strip()
    for c in cmds:
        # Проверяем, что команда - это самостоятельное слово (после нее идет пробел, конец строки или знак препинания)
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


@router.message(Command("id"))
async def cmd_get_topic_id(message: Message):
    if message.message_thread_id:
        await message.answer(f"ID этого топика: <code>{message.message_thread_id}</code>", parse_mode="HTML")
    else:
        await message.answer(f"ID этого чата: <code>{message.chat.id}</code>", parse_mode="HTML")


@router.message(Command("force_scan"))
async def admin_force_scan(message: Message):
    if str(message.from_user.id) not in settings.DEVELOPER_IDS and str(
        message.from_user.id) != settings.FOUNDER_ID: return
    sent_msg = await message.answer("⏳ Собираю данные...")
    from scheduler.jobs import collect_daily_stats
    await collect_daily_stats()
    await sent_msg.edit_text("✅ Готово")
    asyncio.create_task(delete_later(sent_msg, 60))


@router.message(Command("all_reg_list"))
async def cmd_all_reg_list(message: Message, user_repo: UserRepository):
    a_role = await user_repo.get_user_role(message.from_user.id)
    is_founder = str(message.from_user.id) == settings.FOUNDER_ID
    is_dev = str(message.from_user.id) in settings.DEVELOPER_IDS
    if not is_founder and not is_dev and a_role not in ["Президент", "Вице-президент"]: return

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
        sent = await message.answer(text[x:x + 4000], parse_mode="HTML",
                                    link_preview_options=LinkPreviewOptions(is_disabled=True))
        asyncio.create_task(delete_later(sent, 10800))
    try:
        await message.delete()
    except:
        pass


@router.message(lambda msg: is_cmd(msg.text, ["понизить", "демоут"]))
async def cmd_demote(message: Message, user_repo: UserRepository):
    a_role = await user_repo.get_user_role(message.from_user.id)
    is_founder = str(message.from_user.id) == settings.FOUNDER_ID
    if not is_founder and a_role != "Президент": return

    parts = message.text.split()
    target_id, target_name = None, None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = f"@{message.reply_to_message.from_user.username}" if message.reply_to_message.from_user.username else message.reply_to_message.from_user.full_name
    elif len(parts) > 1 and parts[1].startswith("@"):
        target_username = parts[1]
        all_users = await user_repo.get_all_users_for_roles()
        for u in all_users:
            if u["tg_name"] and target_username.lower() in u["tg_name"].lower():
                target_id = u["user_id"]
                target_name = target_username
                break
    if not target_id:
        sent = await message.answer("❌ Укажите @username или ответьте на сообщение.")
        asyncio.create_task(delete_later(sent, 60))
        return
    await user_repo.set_user_role(target_id, "Гость", "Отклонен")
    sent = await message.answer(f"⬇️ <b>{target_name}</b> понижен до Гостя и лишен системных полномочий в боте.",
                                parse_mode="HTML")
    asyncio.create_task(delete_later(sent))


@router.message(lambda msg: is_cmd(msg.text, ["вернуть звание", "восстановить", "вернуть"]))
async def cmd_restore_rank(message: Message, user_repo: UserRepository):
    a_role = await user_repo.get_user_role(message.from_user.id)
    is_founder = str(message.from_user.id) == settings.FOUNDER_ID
    if not is_founder and a_role != "Президент": return

    parts = message.text.split()
    target_id, target_name = None, None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = f"@{message.reply_to_message.from_user.username}" if message.reply_to_message.from_user.username else message.reply_to_message.from_user.full_name
    elif len(parts) > 2 and parts[-1].startswith("@"):
        target_username = parts[-1]
        all_users = await user_repo.get_all_users_for_roles()
        for u in all_users:
            if u["tg_name"] and target_username.lower() in u["tg_name"].lower():
                target_id = u["user_id"]
                target_name = target_username
                break
    if not target_id:
        sent = await message.answer("❌ Укажите @username или ответьте на сообщение.")
        asyncio.create_task(delete_later(sent, 60))
        return
    await user_repo.set_user_role(target_id, "Участник", "Одобрен")
    sent = await message.answer(
        f"✅ Полномочия <b>{target_name}</b> восстановлены. Реальное звание из API игры синхронизируется в течение минуты.",
        parse_mode="HTML")
    asyncio.create_task(delete_later(sent))


@router.message(lambda msg: is_cmd(msg.text, ["мут", "mute", "анмут", "unmute", "кик", "kick", "бан", "ban", "разбан", "unban"]))
async def cmd_moderation(message: Message, bot: Bot, user_repo: UserRepository):
    if str(message.chat.id) == settings.ADMIN_CHAT_ID: return

    a_role = await user_repo.get_user_role(message.from_user.id)
    is_founder = str(message.from_user.id) == settings.FOUNDER_ID

    # Иерархия: Главарь > Президент > Вице-президент (Разработчики вне системы модерации)
    if not is_founder and a_role not in ["Главарь", "Президент", "Вице-президент"]:
        err_msg = await message.answer("❌ У вас нет прав модератора для выполнения этой команды.")
        asyncio.create_task(delete_later(err_msg, 60))
        return

    parts = message.text.split()
    # Очищаем команду от возможных прилипших знаков препинания (например, "бан,")
    cmd = parts[0].lower().strip(string.punctuation)

    target_username = None
    t_arg = None
    reason_parts = []

    # Функция-помощник для определения, является ли слово указателем времени
    def is_time_arg(word: str) -> bool:
        w = word.lower()
        if w.isdigit(): return True
        if w in ["минута", "минуту", "1м", "1m", "час", "1ч", "1h"]: return True
        if w.endswith(("м", "ч", "m", "h")) and w[:-1].isdigit(): return True
        return False

    # Умный парсинг аргументов независимо от их порядка
    for word in parts[1:]:
        if word.startswith("@") and not target_username:
            target_username = word
        elif cmd in ["мут", "mute"] and not t_arg and is_time_arg(word):
            t_arg = word.lower()
        else:
            reason_parts.append(word)

    target_id, target_name = None, None

    # 1. Ищем цель по тегу, если он был найден в сообщении
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

    # 2. Если тега не было, проверяем ответ на сообщение (reply)
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        u = message.reply_to_message.from_user
        target_name = f"@{u.username}" if u.username else u.full_name

    # Если ни тега, ни реплая нет
    if not target_id:
        sent_msg = await message.answer("❌ Ответьте на сообщение пользователя или укажите его @username.")
        asyncio.create_task(delete_later(sent_msg, 60))
        return

    # Обработка времени
    dt = timedelta(minutes=10)  # Дефолт
    time_str = "10 минут"

    if cmd in ["бан", "ban"]:
        dt = None
        time_str = "навсегда"
    elif cmd in ["мут", "mute"] and t_arg:
        parsed_mins = None
        if t_arg.isdigit():
            parsed_mins = int(t_arg)
        elif t_arg in ["минута", "минуту", "1м", "1m"]:
            parsed_mins = 1
        elif t_arg in ["час", "1ч", "1h"]:
            parsed_mins = 60
        elif t_arg.endswith("м") and t_arg[:-1].isdigit():
            parsed_mins = int(t_arg[:-1])
        elif t_arg.endswith("ч") and t_arg[:-1].isdigit():
            parsed_mins = int(t_arg[:-1]) * 60
        elif t_arg.endswith("m") and t_arg[:-1].isdigit():
            parsed_mins = int(t_arg[:-1])
        elif t_arg.endswith("h") and t_arg[:-1].isdigit():
            parsed_mins = int(t_arg[:-1]) * 60

        if parsed_mins is not None:
            dt_minutes = max(1, parsed_mins)
            dt = timedelta(minutes=dt_minutes)

            # Правильное склонение минут
            if dt_minutes % 10 == 1 and dt_minutes % 100 != 11:
                time_str = f"{dt_minutes} минуту"
            elif 2 <= dt_minutes % 10 <= 4 and not (12 <= dt_minutes % 100 <= 14):
                time_str = f"{dt_minutes} минуты"
            else:
                time_str = f"{dt_minutes} минут"

    reason = " ".join(reason_parts) if reason_parts else "Не указана"

    t_role = await user_repo.get_user_role(target_id)
    a_sym = get_combined_symbols(message.from_user.id, a_role)
    t_sym = get_combined_symbols(target_id, t_role)

    fmt_admin = f"{a_sym} <b>{message.from_user.first_name}</b>"
    fmt_target = f"{t_sym} <b>{target_name}</b>"

    try:
        if cmd in ["мут", "mute"]:
            await bot.restrict_chat_member(message.chat.id, target_id,
                                           permissions=ChatPermissions(can_send_messages=False),
                                           until_date=datetime.now() + dt)
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
