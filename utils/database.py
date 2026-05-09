import aiosqlite

DB_NAME = "/app/data/bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                bs_tag TEXT NOT NULL,
                is_approved BOOLEAN DEFAULT 1
            )
        """)
        await db.commit()

async def add_user(user_id: int, bs_tag: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, bs_tag, is_approved) VALUES (?, ?, 1)",
            (user_id, bs_tag)
        )
        await db.commit()

async def is_user_approved(user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT is_approved FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return bool(row) if row else False