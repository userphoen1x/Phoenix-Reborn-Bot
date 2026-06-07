import asyncio
import aiosqlite
import logging
import os
from datetime import date
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from core.config import settings
from database.repositories.chat_repo import ChatRepository
from database.repositories.user_repo import UserRepository
from external.brawl_api import BrawlAPIClient
from external.groq_client import GroqClient
from utils.admin_logger import send_log


async def collect_daily_stats():
    brawl_client = BrawlAPIClient()
    members, _ = await brawl_client.get_all_club_members()
    today = date.today().isoformat()
    async with aiosqlite.connect(settings.DB_PATH) as db:
        chat_repo = ChatRepository(db)
        for m in members:
            tag = m["tag"]
            name = m["name"]
            stats = await brawl_client.get_player_stats(tag)
            if stats:
                await chat_repo.save_snapshot(tag=tag, name=name, dt=today, trophies=stats["trophies"],
                                              solo=stats["solo_wins"], duo=stats["duo_wins"], wins3v3=stats["wins_3v3"],
                                              rank_c=stats.get("ranked_curr_rank", 0), rank_h=0)
            await asyncio.sleep(0.05)


async def run_archivist_summary(bot: Bot):
    if not settings.TARGET_CHAT_ID or not settings.GROQ_KEYS: return
    async with aiosqlite.connect(settings.DB_PATH) as db:
        chat_repo = ChatRepository(db)
        logs_today = await chat_repo.get_today_chat_logs(int(settings.TARGET_CHAT_ID))
        if not logs_today or len(logs_today.strip()) < 50: return
        groq_client = GroqClient()
        system_prompt = "Ты — 'Архивариус' и летописец сообщества Phoenix Reborn. Ты извлекаешь смыслы из хаоса. Твой стиль: кратко, хлестко, иронично. Никакого позитива и приветствий.\n\nПРАВИЛА:\n1. Используй ТОЛЬКО HTML-теги <b>текст</b> для жирного шрифта. Звездочки (*) ЗАПРЕЩЕНЫ.\n2. Выделяй жирным имена участников и ключевые темы.\n\nСТРУКТУРА ОТВЕТА:\n🔥 <b>ГЛАВНОЕ СОБЫТИЕ</b>\n(Описание инфоповода)\n\n🗣 <b>ОСНОВНЫЕ ТЕМЫ ДНЯ</b>\n(3-5 тем. Кратко.)"
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Логи:\n\n{logs_today}"}]
        summary_text = groq_client.ask(messages, max_tokens=600)
        if "❌" not in summary_text:
            await bot.send_message(chat_id=int(settings.TARGET_CHAT_ID), text=summary_text, parse_mode="HTML")
            await send_log(bot, "TOPIC_ARCHIVIST", f"📜 <b>Сводка Архивариуса</b>\n\n{summary_text}")
        await chat_repo.clear_old_chat_logs()


async def check_roles(bot: Bot):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        user_repo = UserRepository(db)
        brawl_client = BrawlAPIClient()

        db_users = await user_repo.get_all_users_for_roles()
        clubs_members, _ = await brawl_client.get_all_club_members()

        api_roles = {}
        if clubs_members:
            for m in clubs_members:
                role_eng = m.get("role", "member")
                role_ru = {"president": "Президент", "vicePresident": "Вице-президент", "senior": "Ветеран",
                           "member": "Участник"}.get(role_eng, "Участник")
                api_roles[m.get("tag")] = role_ru

        for user in db_users:
            u_id = user["user_id"]
            tag = user["tag"]
            db_role = user["game_role"]
            db_status = user["role_status"]
            tg_name = user["tg_name"]
            player_name = user["name"]
            club_name = user["club_name"]

            display_tg = tg_name if tg_name and tg_name.startswith("@") else f"@{tg_name}" if tg_name else "Игрок"

            try:
                member = await bot.get_chat_member(int(settings.TARGET_CHAT_ID), u_id)
                in_chat = member.status in ['member', 'administrator', 'creator', 'restricted']
                is_banned = member.status == 'kicked'
            except Exception:
                in_chat = False
                is_banned = False

            if is_banned:
                continue

            in_club = tag in api_roles

            if not in_club:
                if in_chat and db_role != "Гость":
                    await user_repo.set_user_role(u_id, "Гость", "Одобрен")
            else:
                actual_role = api_roles[tag]
                if actual_role != db_role:
                    if actual_role in ["Президент", "Вице-президент"]:
                        await user_repo.set_user_role(u_id, actual_role, "Ожидает")

                        if settings.FOUNDER_ID:
                            role_eng = "president" if actual_role == "Президент" else "vicePresident"
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="Да", callback_data=f"role_approve:{u_id}:{role_eng}")],
                                [InlineKeyboardButton(text="Нет", callback_data=f"role_reject:{u_id}")]
                            ])
                            msg_text = f"👤 {display_tg} (ID: <code>{u_id}</code>)\n🎮 Игрок: <b>{player_name}</b> (<code>{tag}</code>)\n🏰 Клуб: <b>{club_name}</b>\n\nПолучил звание <b>{actual_role}</b> в игре. Подтверждаете выдачу внутренних модераторских прав в боте?"
                            try:
                                await bot.send_message(settings.FOUNDER_ID, msg_text, reply_markup=kb,
                                                       parse_mode="HTML")
                            except:
                                pass
                    else:
                        await user_repo.set_user_role(u_id, actual_role, "Одобрен")
                elif actual_role == db_role and db_status == "Отклонен":
                    pass


async def backup_database(bot: Bot):
    if not settings.ADMIN_CHAT_ID or not settings.TOPIC_BACKUP: return
    if not os.path.exists(settings.DB_PATH):
        logging.warning("Файл БД не найден для создания бэкапа.")
        return
    try:
        db_file = FSInputFile(settings.DB_PATH, filename=f"PR_Backup_{date.today().isoformat()}.db")
        await bot.send_document(chat_id=int(settings.ADMIN_CHAT_ID), message_thread_id=int(settings.TOPIC_BACKUP),
                                document=db_file,
                                caption=f"📦 <b>Ежедневный бэкап базы данных</b>\n📅 Дата: {date.today().isoformat()}",
                                parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка при отправке бэкапа: {e}")