import aiosqlite
import os
import json
from datetime import datetime, date, timedelta

DB_NAME = "/app/data/bot_data_v3.db"

ROLE_SYMBOLS = {
    "Основатель": "👑",
    "Программист": "👨‍💻",
    "Президент": "🌟",
    "Вице-президент": "⭐",
    "Ветеран": "🎖",
    "Участник": "👤",
    "Гость": "👻"
}


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS users
                         (
                             user_id
                             INTEGER
                             PRIMARY
                             KEY,
                             bs_tag
                             TEXT
                             NOT
                             NULL,
                             player_name
                             TEXT,
                             club_name
                             TEXT,
                             is_approved
                             BOOLEAN
                             DEFAULT
                             1
                         )
                         """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS tg_profiles
                         (
                             user_id
                             INTEGER
                             PRIMARY
                             KEY,
                             full_name
                             TEXT
                         )
                         """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS links
                         (
                             link
                             TEXT
                             PRIMARY
                             KEY,
                             user_id
                             INTEGER
                         )
                         """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS messages
                         (
                             user_id
                             INTEGER,
                             chat_id
                             INTEGER,
                             msg_date
                             DATE,
                             msg_count
                             INTEGER
                             DEFAULT
                             1,
                             PRIMARY
                             KEY
                         (
                             user_id,
                             chat_id,
                             msg_date
                         )
                             )
                         """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS bs_snapshots
                         (
                             tag
                             TEXT,
                             name
                             TEXT,
                             record_date
                             DATE,
                             trophies
                             INTEGER,
                             solo_wins
                             INTEGER,
                             duo_wins
                             INTEGER,
                             wins_3v3
                             INTEGER,
                             rank_current
                             INTEGER,
                             rank_highest
                             INTEGER,
                             PRIMARY
                             KEY
                         (
                             tag,
                             record_date
                         )
                             )
                         """)
        await db.commit()


async def upgrade_db_roles():
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("ALTER TABLE tg_profiles ADD COLUMN game_role TEXT DEFAULT 'Гость'")
            await db.execute("ALTER TABLE tg_profiles ADD COLUMN role_status TEXT DEFAULT 'Одобрен'")
            await db.commit()
        except Exception:
            pass


async def upgrade_db_economy():
    async with aiosqlite.connect(DB_NAME) as db:
        cols = [
            ("balance", "INTEGER DEFAULT 1000"),
            ("xp", "INTEGER DEFAULT 0"),
            ("level", "INTEGER DEFAULT 1"),
            ("bot_class", "TEXT DEFAULT 'Новичок'"),
            ("last_work", "TEXT DEFAULT NULL"),
            ("inventory", "TEXT DEFAULT '{}'")
        ]
        for col_name, col_type in cols:
            try:
                await db.execute(f"ALTER TABLE tg_profiles ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass
        await db.commit()


async def add_user(user_id: int, bs_tag: str, player_name: str, club_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, bs_tag, player_name, club_name, is_approved) VALUES (?, ?, ?, ?, 1)",
            (user_id, bs_tag, player_name, club_name))
        await db.execute("INSERT OR IGNORE INTO tg_profiles (user_id, full_name, balance) VALUES (?, ?, 1000)",
                         (user_id, player_name))
        await db.commit()


async def get_user_data(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        query = """
                SELECT u.player_name, u.club_name, u.is_approved, t.full_name
                FROM users u
                         LEFT JOIN tg_profiles t ON u.user_id = t.user_id
                WHERE u.user_id = ? \
                """
        async with db.execute(query, (user_id,)) as cursor:
            return await cursor.fetchone()


async def get_eco_data(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        query = """
                SELECT t.balance, t.xp, t.level, t.bot_class, t.last_work, t.inventory, u.bs_tag
                FROM tg_profiles t
                         LEFT JOIN users u ON t.user_id = u.user_id
                WHERE t.user_id = ? \
                """
        async with db.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "balance": row[0], "xp": row[1], "level": row[2],
                    "bot_class": row[3], "last_work": row[4],
                    "inventory": json.loads(row[5]) if row[5] else {},
                    "bs_tag": row[6]
                }
            return None


async def update_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE tg_profiles SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()


async def set_eco_data(user_id: int, col: str, value):
    async with aiosqlite.connect(DB_NAME) as db:
        if isinstance(value, dict):
            value = json.dumps(value)
        await db.execute(f"UPDATE tg_profiles SET {col} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()


async def get_user_role_by_id(user_id: int):
    founder_id = os.getenv("FOUNDER_ID")
    admin_id = os.getenv("ADMIN_ID")
    if founder_id and str(user_id) == str(founder_id):
        return "Основатель"
    if admin_id and str(user_id) == str(admin_id):
        return "Программист"

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT game_role FROM tg_profiles WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "Гость"


async def save_link(link: str, user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO links (link, user_id) VALUES (?, ?)", (link, user_id))
        await db.commit()


async def get_link_owner(link: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM links WHERE link = ?", (link,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def increment_message(user_id: int, chat_id: int, full_name: str):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO tg_profiles (user_id, full_name) VALUES (?, ?)", (user_id, full_name))
        await db.execute("""
                         INSERT INTO messages (user_id, chat_id, msg_date, msg_count)
                         VALUES (?, ?, ?, 1) ON CONFLICT(user_id, chat_id, msg_date) DO
                         UPDATE SET msg_count = msg_count + 1
                         """, (user_id, chat_id, today))
        await db.commit()


async def save_snapshot(tag: str, name: str, dt: str, trophies: int, solo: int, duo: int, wins3v3: int, rank_c: int,
                        rank_h: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR REPLACE INTO bs_snapshots 
            (tag, name, record_date, trophies, solo_wins, duo_wins, wins_3v3, rank_current, rank_highest)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tag, name, dt, trophies, solo, duo, wins3v3, rank_c, rank_h))
        await db.commit()


async def get_all_approved_tags():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT bs_tag FROM users WHERE is_approved = 1") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_top_messages(days=None):
    query = """
            SELECT t.full_name, u.player_name, SUM(m.msg_count) as total, m.user_id
            FROM messages m
                     LEFT JOIN tg_profiles t ON m.user_id = t.user_id
                     LEFT JOIN users u ON m.user_id = u.user_id \
            """
    params = []
    if days is not None:
        td = (date.today() - timedelta(days=days)).isoformat()
        query += " WHERE m.msg_date >= ? "
        params.append(td)
    query += " GROUP BY m.user_id ORDER BY total DESC LIMIT 10"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()


async def get_baseline_trophies(days: int, tags_filter: list = None) -> dict:
    if tags_filter is not None and len(tags_filter) == 0: return {}

    # День логически начинается ровно в 00:00 (время фотки кубков)
    logical_today = datetime.now().date()
    td = (logical_today - timedelta(days=days - 1)).isoformat()

    query = """
            SELECT tag, trophies
            FROM bs_snapshots s1
            WHERE record_date = (SELECT MIN(record_date) \
                                 FROM bs_snapshots s2 \
                                 WHERE s2.tag = s1.tag \
                                   AND s2.record_date >= ?) \
            """
    params = [td]
    if tags_filter:
        placeholders = ",".join("?" for _ in tags_filter)
        query += f" AND s1.tag IN ({placeholders})"
        params.extend(tags_filter)

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


async def get_top_gain(column: str, days: int, tags_filter: list = None):
    # Эта функция больше не нужна, так как мы считаем рост напрямую из игры,
    # но оставляем для совместимости со старыми вызовами.
    pass


async def get_top_absolute(column: str, tags_filter: list = None, use_max: bool = False):
    if tags_filter is not None and len(tags_filter) == 0: return []
    if use_max:
        query = f"SELECT name, MAX({column}) as val FROM bs_snapshots s WHERE 1=1"
    else:
        query = f"SELECT name, ({column}) as val FROM bs_snapshots s WHERE record_date = (SELECT MAX(record_date) FROM bs_snapshots WHERE tag = s.tag)"
    params = []
    if tags_filter:
        placeholders = ",".join("?" for _ in tags_filter)
        query += f" AND tag IN ({placeholders})"
        params.extend(tags_filter)
    query += " GROUP BY tag ORDER BY val DESC LIMIT 10"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()


async def get_top_balance(limit: int = 10):
    async with aiosqlite.connect(DB_NAME) as db:
        query = """
                SELECT t.full_name, u.player_name, t.balance, t.user_id
                FROM tg_profiles t
                         LEFT JOIN users u ON t.user_id = u.user_id
                WHERE t.balance > 0
                ORDER BY t.balance DESC LIMIT ? \
                """
        async with db.execute(query, (limit,)) as cursor:
            return await cursor.fetchall()


async def get_tag_to_tg_map():
    async with aiosqlite.connect(DB_NAME) as db:
        query = """
                SELECT u.bs_tag, u.user_id, t.full_name
                FROM users u
                         LEFT JOIN tg_profiles t ON u.user_id = t.user_id
                WHERE u.is_approved = 1 \
                """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: {"id": row[1], "name": row[2]} for row in rows}


async def set_user_role(user_id: int, role: str, status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE tg_profiles SET game_role = ?, role_status = ? WHERE user_id = ?",
                         (role, status, user_id))
        await db.commit()


async def get_all_users_for_roles():
    async with aiosqlite.connect(DB_NAME) as db:
        query = """
                SELECT u.user_id, u.bs_tag, u.player_name, t.game_role, t.role_status, t.full_name
                FROM users u
                         JOIN tg_profiles t ON u.user_id = t.user_id
                WHERE u.is_approved = 1 \
                """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [
                {"user_id": r[0], "tag": r[1], "name": r[2], "game_role": r[3], "role_status": r[4], "tg_name": r[5]}
                for r in rows]