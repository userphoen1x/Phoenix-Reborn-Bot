import aiosqlite
import logging
from core.config import settings

async def init_db():
    try:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, bs_tag TEXT NOT NULL, player_name TEXT, club_name TEXT, is_approved BOOLEAN DEFAULT 1)")
            await db.execute("CREATE TABLE IF NOT EXISTS tg_profiles (user_id INTEGER PRIMARY KEY, full_name TEXT)")
            await db.execute("CREATE TABLE IF NOT EXISTS links (link TEXT PRIMARY KEY, user_id INTEGER)")
            await db.execute("CREATE TABLE IF NOT EXISTS messages (user_id INTEGER, chat_id INTEGER, msg_date DATE, msg_count INTEGER DEFAULT 1, PRIMARY KEY (user_id, chat_id, msg_date))")
            await db.execute("CREATE TABLE IF NOT EXISTS bs_snapshots (tag TEXT, name TEXT, record_date DATE, trophies INTEGER, solo_wins INTEGER, duo_wins INTEGER, wins_3v3 INTEGER, rank_current INTEGER, rank_highest INTEGER, PRIMARY KEY (tag, record_date))")
            await db.execute("CREATE TABLE IF NOT EXISTS chat_logs (chat_id INTEGER, user_id INTEGER, full_name TEXT, text TEXT, msg_timestamp DATETIME)")
            await db.execute("CREATE TABLE IF NOT EXISTS chat_modes (chat_id INTEGER PRIMARY KEY, mode TEXT DEFAULT 'default')")
            try:
                await db.execute("ALTER TABLE tg_profiles ADD COLUMN game_role TEXT DEFAULT 'Гость'")
                await db.execute("ALTER TABLE tg_profiles ADD COLUMN role_status TEXT DEFAULT 'Одобрен'")
            except aiosqlite.OperationalError:
                pass
            
            # Убрали XP и Уровень, оставили только нужные экономические колонки
            eco_cols = [
                ("balance", "INTEGER DEFAULT 1000"),
                ("bot_class", "TEXT DEFAULT 'Новичок'"),
                ("last_work", "TEXT DEFAULT NULL"),
                ("inventory", "TEXT DEFAULT '{}'"),
                ("last_robbery", "TEXT DEFAULT NULL")
            ]
            for col_name, col_type in eco_cols:
                try:
                    await db.execute(f"ALTER TABLE tg_profiles ADD COLUMN {col_name} {col_type}")
                except aiosqlite.OperationalError:
                    pass
            await db.commit()
    except Exception as e:
        logging.critical(e)
        raise
