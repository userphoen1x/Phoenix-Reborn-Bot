import aiosqlite

DB_NAME = "/app/data/bot_data.db"

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
