async def get_all_approved_tags():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT bs_tag FROM users WHERE is_approved = 1") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def save_snapshot(tag: str, date: str, trophies: int, solo: int, duo: int, wins3v3: int, rank_c: int, rank_h: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR REPLACE INTO bs_snapshots 
            (tag, record_date, trophies, solo_wins, duo_wins, wins_3v3, rank_current, rank_highest)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (tag, date, trophies, solo, duo, wins3v3, rank_c, rank_h))
        await db.commit()