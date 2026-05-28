from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from scheduler.jobs import collect_daily_stats, run_archivist_summary, check_roles, backup_database


def start_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    scheduler.add_job(collect_daily_stats, 'cron', hour=4, minute=0)
    scheduler.add_job(run_archivist_summary, 'cron', hour=23, minute=30, args=[bot])

    scheduler.add_job(backup_database, 'cron', hour=12, minute=0, args=[bot])

    scheduler.add_job(check_roles, 'interval', minutes=1, args=[bot])
    scheduler.start()