import aiosqlite
from datetime import date, timedelta

DB_NAME = "/app/data/bot_data_v3.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                bs_tag TEXT NOT NULL,
                player_name TEXT,
                club_name TEXT,
                is_approved BOOLEAN DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tg_profiles (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS links (
                link TEXT PRIMARY KEY,
                user_id INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                user_id INTEGER,
                chat_id INTEGER,
                msg_date DATE,
                msg_count INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, chat_id, msg_date)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bs_snapshots (
                tag TEXT,
                name TEXT,
                record_date DATE,
                trophies INTEGER,
                solo_wins INTEGER,
                duo_wins INTEGER,
                wins_3v3 INTEGER,
                rank_current INTEGER,
                rank_highest INTEGER,
                PRIMARY KEY (tag, record_date)
            )
        """)
        await db.commit()

async def add_user(user_id: int, bs_tag: str, player_name: str, club_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO users (user_id, bs_tag, player_name, club_name, is_approved) VALUES (?, ?, ?, ?, 1)", (user_id, bs_tag, player_name, club_name))
        await db.commit()

async def get_user_data(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT player_name, club_name, is_approved FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

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
        await db.execute("INSERT OR REPLACE INTO tg_profiles (user_id, full_name) VALUES (?, ?)", (user_id, full_name))
        await db.execute("""
            INSERT INTO messages (user_id, chat_id, msg_date, msg_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, chat_id, msg_date) DO UPDATE SET msg_count = msg_count + 1
        """, (user_id, chat_id, today))
        await db.commit()

async def save_snapshot(tag: str, name: str, dt: str, trophies: int, solo: int, duo: int, wins3v3: int, rank_c: int, rank_h: int):
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
    query = "SELECT t.full_name, SUM(m.msg_count) as total FROM messages m JOIN tg_profiles t ON m.user_id = t.user_id "
    params = []
    if days is not None:
        td = (date.today() - timedelta(days=days)).isoformat()
        query += " WHERE m.msg_date >= ? "
        params.append(td)
    query += " GROUP BY m.user_id ORDER BY total DESC LIMIT 10"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, params) as cursor: return await cursor.fetchall()

async def get_top_gain(column: str, days: int, tags_filter: list = None):
    if tags_filter is not None and len(tags_filter) == 0: return []
    td = (date.today() - timedelta(days=days)).isoformat()
    query = f"""
        SELECT name,
               (SELECT {column} FROM bs_snapshots WHERE tag = s.tag ORDER BY record_date DESC LIMIT 1) -
               (SELECT {column} FROM bs_snapshots WHERE tag = s.tag AND record_date >= ? ORDER BY record_date ASC LIMIT 1) as gain
        FROM bs_snapshots s
        WHERE 1=1
    """
    params = [td]
    if tags_filter:
        placeholders = ",".join("?" for _ in tags_filter)
        query += f" AND s.tag IN ({placeholders})"
        params.extend(tags_filter)
    query += " GROUP BY tag HAVING gain > 0 ORDER BY gain DESC LIMIT 10"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, params) as cursor: return await cursor.fetchall()

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
        async with db.execute(query, params) as cursor: return await cursor.fetchall()

async def get_tag_to_tg_map():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT bs_tag, user_id FROM users WHERE is_approved = 1") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}