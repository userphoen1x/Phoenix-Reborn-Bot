import asyncio
import logging
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.brawl_api import get_all_club_members, get_player_stats
from utils.database import save_snapshot


async def collect_daily_stats():
    logging.info("Начинаю ночной сбор статистики по ВСЕМ участникам клубов...")
    members = await get_all_club_members()
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
                rank_c=stats["rank_current"],
                rank_h=stats["rank_highest"]
            )
        await asyncio.sleep(0.05)

    logging.info("Сбор статистики завершен успешно!")


def start_scheduler():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(collect_daily_stats, 'cron', hour=4, minute=0)
    scheduler.start()