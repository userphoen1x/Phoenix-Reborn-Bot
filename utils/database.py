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
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, bs_tag, player_name, club_name, is_approved) VALUES (?, ?, ?, ?, 1)",
            (user_id, bs_tag, player_name, club_name)
        )
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

async def increment_message(user_id: int, chat_id: int):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO messages (user_id, chat_id, msg_date, msg_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, chat_id, msg_date) 
            DO UPDATE SET msg_count = msg_count + 1
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
    async with aiosqlite.connect(DB_NAME) as db:
        if days is None:
            query = "SELECT u.player_name, SUM(m.msg_count) as total FROM messages m JOIN users u ON m.user_id = u.user_id GROUP BY m.user_id ORDER BY total DESC LIMIT 10"
            async with db.execute(query) as cursor: return await cursor.fetchall()
        else:
            td = (date.today() - timedelta(days=days)).isoformat()
            query = "SELECT u.player_name, SUM(m.msg_count) as total FROM messages m JOIN users u ON m.user_id = u.user_id WHERE m.msg_date >= ? GROUP BY m.user_id ORDER BY total DESC LIMIT 10"
            async with db.execute(query, (td,)) as cursor: return await cursor.fetchall()

async def get_top_gain(column: str, days: int):
    td = (date.today() - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        query = f"""
            SELECT name,
                   (SELECT {column} FROM bs_snapshots WHERE tag = s.tag ORDER BY record_date DESC LIMIT 1) -
                   (SELECT {column} FROM bs_snapshots WHERE tag = s.tag AND record_date >= ? ORDER BY record_date ASC LIMIT 1) as gain
            FROM bs_snapshots s
            GROUP BY tag
            HAVING gain > 0
            ORDER BY gain DESC LIMIT 10
        """
        async with db.execute(query, (td,)) as cursor:
            return await cursor.fetchall()

async def get_top_absolute(column: str):
    async with aiosqlite.connect(DB_NAME) as db:
        query = f"""
            SELECT name, ({column}) as val
            FROM bs_snapshots s
            WHERE record_date = (SELECT MAX(record_date) FROM bs_snapshots WHERE tag = s.tag)
            GROUP BY tag
            ORDER BY val DESC LIMIT 10
        """
        async with db.execute(query) as cursor:
            return await cursor.fetchall()