import asyncio
import logging
import os
import groq
from datetime import date, datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import AsyncGroq
from utils.brawl_api import get_all_club_members, get_player_stats
from utils.database import save_snapshot, get_all_users_for_roles, set_user_role, get_today_chat_logs, \
    clear_old_chat_logs

CHEAP_MODEL = "llama-3.1-8b-instant"


async def collect_daily_stats():
    logging.info("START DAILY SNAPSHOT RESET (4:00 MSK)")
    members, _ = await get_all_club_members()
    today = date.today().isoformat()
    for m in members:
        tag = m["tag"]
        name = m["name"]
        stats = await get_player_stats(tag)
        if stats:
            await save_snapshot(
                tag=tag,
                name=name,
                dt=today,
                trophies=stats["trophies"],
                solo=stats["solo_wins"],
                duo=stats["duo_wins"],
                wins3v3=stats["wins_3v3"],
                rank_c=stats.get("ranked_curr_rank", 0),
                rank_h=0
            )
        await asyncio.sleep(0.05)
    logging.info("END DAILY SNAPSHOT RESET")


async def run_archivist_summary(bot: Bot):
    logging.info("START ARCHIVIST DAILY SUMMARY")
    target_chat = os.getenv("TARGET_CHAT_ID")

    keys = [os.getenv(f"GROQ_API_KEY_{i}") for i in range(1, 4)]
    keys = [k for k in keys if k]

    if not target_chat:
        logging.warning("Пропустил сводку: не задан TARGET_CHAT_ID")
        return
    if not keys:
        logging.warning("Пропустил сводку: не заданы ключи GROQ_API_KEY")
        return

    logs_today = await get_today_chat_logs(int(target_chat))
    if not logs_today or len(logs_today.strip()) < 50:
        logging.info("Чат сегодня был слишком неактивен для сводки.")
        return

    system_prompt = (
        "Ты — 'Архивариус' и летописец сообщества Phoenix Reborn. Ты извлекаешь смыслы из хаоса. "
        "Твой стиль: кратко, хлестко, иронично, по-ветерански. Никакого позитива и приветствий.\n\n"
        "ПРАВИЛА:\n"
        "1. Используй ТОЛЬКО HTML-теги <b>текст</b> для жирного шрифта. Звездочки (*) КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНЫ.\n"
        "2. Выделяй жирным имена участников и ключевые темы.\n"
        "3. Ты всегда на стороне Phoenix Reborn.\n\n"
        "СТРУКТУРА ОТВЕТА:\n"
        "🔥 <b>ГЛАВНОЕ СОБЫТИЕ</b>\n(Описание ключевого инфоповода дня)\n\n"
        "🗣 <b>ОСНОВНЫЕ ТЕМЫ ДНЯ</b>\n(3-5 тем с упоминанием зачинщиков через <b>имя</b>. Кратко, по 2-3 предложения.)"
    )

    # Каскадная система: пробуем ключи по очереди для обработки логов
    for key in keys:
        client = AsyncGroq(api_key=key)
        try:
            response = await client.chat.completions.create(
                model=CHEAP_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Вот логи сегодняшнего общения:\n\n{logs_today}"}
                ],
                temperature=0.7
            )
            summary_text = response.choices[0].message.content
            await bot.send_message(chat_id=int(target_chat), text=summary_text, parse_mode="HTML")
            break  # Успешно выполнили - выходим из цикла ключей
        except groq.RateLimitError:
            logging.warning("⚠️ Архивариус: Лимит ключа. Переключаюсь на следующий...")
            continue
        except Exception as e:
            logging.error(f"Ошибка Архивариуса: {e}")
            break

    await clear_old_chat_logs()
    logging.info("END ARCHIVIST DAILY SUMMARY")


async def check_roles(bot: Bot):
    members, _ = await get_all_club_members()
    api_roles = {}
    role_translation = {"president": "Президент", "vicePresident": "Вице-президент", "senior": "Ветеран",
                        "member": "Участник"}

    for m in members:
        api_roles[m["tag"]] = role_translation.get(m.get("role", "member"), "Участник")

    db_users = await get_all_users_for_roles()
    founder_id = os.getenv("FOUNDER_ID")
    target_chat = os.getenv("TARGET_CHAT_ID")

    for user in db_users:
        u_id = user["user_id"]
        tag = user["tag"]
        db_role = user["game_role"]
        status = user["role_status"]
        name = user["name"]
        tg_name = user.get("tg_name") or "Игрок"

        if tag not in api_roles:
            if db_role != "Гость":
                await set_user_role(u_id, "Гость", "Одобрен")
                if target_chat:
                    try:
                        await bot.promote_chat_member(chat_id=target_chat, user_id=u_id, can_manage_chat=False)
                    except:
                        pass
        else:
            api_role = api_roles[tag]
            if api_role == db_role: continue

            if api_role in ["Участник", "Ветеран"]:
                await set_user_role(u_id, api_role, "Одобрен")
                if target_chat and db_role in ["Президент", "Вице-президент"]:
                    try:
                        await bot.promote_chat_member(chat_id=target_chat, user_id=u_id, can_manage_chat=False)
                    except:
                        pass
            elif api_role in ["Президент", "Вице-президент"]:
                if status in ["Ожидает", "Отклонен"]: continue
                await set_user_role(u_id, db_role, "Ожидает")
                if founder_id:
                    role_eng = "president" if api_role == "Президент" else "vicePresident"
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Да", callback_data=f"role_approve:{u_id}:{role_eng}")],
                        [InlineKeyboardButton(text="Нет", callback_data=f"role_reject:{u_id}")]
                    ])
                    try:
                        msg_text = f"{tg_name} ({u_id}) зашел с тега игрока {tag} ({name}). Убедитесь, что это он и выдайте ему права и звание {api_role}."
                        await bot.send_message(founder_id, msg_text, reply_markup=kb)
                    except:
                        pass


def start_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(collect_daily_stats, 'cron', hour=4, minute=0)
    scheduler.add_job(run_archivist_summary, 'cron', hour=23, minute=30, args=[bot])
    scheduler.add_job(check_roles, 'interval', minutes=1, args=[bot])
    scheduler.start()