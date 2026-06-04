import aiosqlite
from typing import Dict, List, Tuple, Optional
from core.config import settings

class UserRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def add_user(self, user_id: int, bs_tag: str, player_name: str, club_name: str):
        await self.db.execute("DELETE FROM users WHERE bs_tag = ?", (bs_tag,))
        await self.db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await self.db.execute("INSERT INTO users (user_id, bs_tag, player_name, club_name, is_approved) VALUES (?, ?, ?, ?, 1)", (user_id, bs_tag, player_name, club_name))
        await self.db.execute("INSERT OR IGNORE INTO tg_profiles (user_id, full_name, balance, game_role) VALUES (?, ?, 1000, 'Гость')", (user_id, player_name))
        await self.db.commit()

    async def get_user_data(self, user_id: int) -> Optional[Tuple]:
        query = "SELECT u.player_name, u.club_name, u.is_approved, t.full_name FROM users u LEFT JOIN tg_profiles t ON u.user_id = t.user_id WHERE u.user_id = ?"
        async with self.db.execute(query, (user_id,)) as cursor:
            return await cursor.fetchone()

    async def get_user_role(self, user_id: int) -> str:
        async with self.db.execute("SELECT game_role FROM tg_profiles WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "Гость"

    async def set_user_role(self, user_id: int, role: str, status: str):
        await self.db.execute("UPDATE tg_profiles SET game_role = ?, role_status = ? WHERE user_id = ?", (role, status, user_id))
        await self.db.commit()

    async def unlink_user_tag(self, target_username: str) -> bool:
        async with self.db.execute("SELECT user_id FROM tg_profiles WHERE full_name = ? COLLATE NOCASE", (target_username,)) as cursor:
            row = await cursor.fetchone()
            if not row: return False
            user_id = row[0]
            await self.db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            await self.db.execute("UPDATE tg_profiles SET game_role = 'Гость' WHERE user_id = ?", (user_id,))
            await self.db.commit()
            return True

    async def get_all_users_for_roles(self) -> List[Dict]:
        query = "SELECT u.user_id, u.bs_tag, u.player_name, t.game_role, t.role_status, t.full_name, u.club_name FROM users u JOIN tg_profiles t ON u.user_id = t.user_id WHERE u.is_approved = 1"
        async with self.db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [{"user_id": r[0], "tag": r[1], "name": r[2], "game_role": r[3], "role_status": r[4], "tg_name": r[5], "club_name": r[6] if r[6] else "Без клуба"} for r in rows]

    async def get_all_registered_users(self) -> List[Tuple]:
        query = "SELECT t.full_name, u.bs_tag, u.player_name FROM users u JOIN tg_profiles t ON u.user_id = t.user_id WHERE u.is_approved = 1 ORDER BY u.player_name"
        async with self.db.execute(query) as cursor:
            return await cursor.fetchall()

    async def get_tag_to_tg_map(self) -> Dict[str, Dict]:
        query = "SELECT u.bs_tag, u.user_id, t.full_name FROM users u LEFT JOIN tg_profiles t ON u.user_id = t.user_id WHERE u.is_approved = 1"
        async with self.db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: {"id": row[1], "name": row[2]} for row in rows}

    async def register_user(self, user_id: int, tag: str, player_name: str, tg_name: str):
        cursor = await self.db.execute("SELECT user_id FROM tg_profiles WHERE user_id = ?", (user_id,))
        exists = await cursor.fetchone()

        if exists:
            await self.db.execute(
                "UPDATE tg_profiles SET full_name = ? WHERE user_id = ?",
                (tg_name, user_id)
            )
        else:
            await self.db.execute(
                "INSERT INTO tg_profiles (user_id, full_name, game_role, role_status) VALUES (?, ?, 'Гость', 'Одобрен')",
                (user_id, tg_name)
            )
        await self.db.commit()