import asyncio
import logging
import os
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.brawl_api import get_all_club_members, get_player_stats
from utils.database import save_snapshot, get_all_users_for_roles, set_user_role


async def collect_daily_stats():
    logging.info("START SCAN")
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
    logging.info("END SCAN")


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
            if api_role == db_role:
                continue

            if api_role in ["Участник", "Ветеран"]:
                await set_user_role(u_id, api_role, "Одобрен")
                if target_chat and db_role in ["Президент", "Вице-президент"]:
                    try:
                        await bot.promote_chat_member(chat_id=target_chat, user_id=u_id, can_manage_chat=False)
                    except:
                        pass
            elif api_role in ["Президент", "Вице-президент"]:
                if status in ["Ожидает", "Отклонен"]:
                    continue

                await set_user_role(u_id, db_role, "Ожидает")
                if founder_id:
                    role_eng = "president" if api_role == "Президент" else "vicePresident"
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Да", callback_data=f"role_approve:{u_id}:{role_eng}")],
                        [InlineKeyboardButton(text="Нет", callback_data=f"role_reject:{u_id}")]
                    ])
                    try:
                        await bot.send_message(founder_id,
                                               f"Пользователь {name} получил в игре звание {api_role}. Выдать полномочия в чате?",
                                               reply_markup=kb)
                    except:
                        pass


def start_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(collect_daily_stats, 'cron', hour=4, minute=0)
    scheduler.add_job(check_roles, 'interval', minutes=1, args=[bot])
    scheduler.start()