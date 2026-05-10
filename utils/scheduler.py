import asyncio
import logging
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.brawl_api import get_all_club_members, get_player_stats
from utils.database import save_snapshot

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
                rank_c=stats["exp_level"],
                rank_h=stats["highest_trophies"]
            )
        await asyncio.sleep(1.0)
    logging.info("END SCAN")

def start_scheduler():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(collect_daily_stats, 'cron', hour=4, minute=0)
    scheduler.start()