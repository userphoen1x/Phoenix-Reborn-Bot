import aiosqlite
import json
from typing import Dict, Any, List, Tuple

class EconomyRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def get_eco_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT t.balance, t.xp, t.level, t.bot_class, t.last_work, t.inventory, u.bs_tag FROM tg_profiles t LEFT JOIN users u ON t.user_id = u.user_id WHERE t.user_id = ?"
        async with self.db.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"balance": row[0], "xp": row[1], "level": row[2], "bot_class": row[3], "last_work": row[4], "inventory": json.loads(row[5]) if row[5] else {}, "bs_tag": row[6]}
            return None

    async def update_balance(self, user_id: int, amount: int):
        await self.db.execute("UPDATE tg_profiles SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await self.db.commit()

    async def set_eco_data(self, user_id: int, col: str, value: Any):
        if isinstance(value, dict):
            value = json.dumps(value)
        await self.db.execute(f"UPDATE tg_profiles SET {col} = ? WHERE user_id = ?", (value, user_id))
        await self.db.commit()

    async def get_top_balance(self, limit: int = 10) -> List[Tuple]:
        query = "SELECT t.full_name, u.player_name, t.balance, t.user_id FROM tg_profiles t LEFT JOIN users u ON t.user_id = u.user_id WHERE t.balance > 0 ORDER BY t.balance DESC LIMIT ?"
        async with self.db.execute(query, (limit,)) as cursor:
            return await cursor.fetchall()

    async def reset_all_balances(self, default_value: int = 1000):
        await self.db.execute("UPDATE tg_profiles SET balance = ?", (default_value,))
        await self.db.commit()