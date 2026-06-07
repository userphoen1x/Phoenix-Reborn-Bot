import aiosqlite
import json
from typing import Optional

class GameRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def init_table(self):
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS active_games (
                user_id INTEGER PRIMARY KEY,
                game_type TEXT,
                state_json TEXT
            )
        """)
        await self.db.commit()

    async def save_game(self, user_id: int, game_type: str, state: dict):
        state_str = json.dumps(state, ensure_ascii=False)
        await self.db.execute(
            "INSERT OR REPLACE INTO active_games (user_id, game_type, state_json) VALUES (?, ?, ?)",
            (user_id, game_type, state_str)
        )
        await self.db.commit()

    async def get_game(self, user_id: int) -> Optional[dict]:
        cursor = await self.db.execute("SELECT game_type, state_json FROM active_games WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return {"game_type": row[0], "state": json.loads(row[1])}
        return None

    async def delete_game(self, user_id: int):
        await self.db.execute("DELETE FROM active_games WHERE user_id = ?", (user_id,))
        await self.db.commit()