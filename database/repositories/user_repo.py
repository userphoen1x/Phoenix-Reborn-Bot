import aiosqlite
from typing import List, Dict, Any, Optional


class UserRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def get_all_users_for_roles(self) -> List[Dict[str, Any]]:
        cursor = await self.db.execute("""
                                       SELECT u.user_id,
                                              u.bs_tag      as tag,
                                              u.player_name as name,
                                              p.game_role,
                                              p.role_status,
                                              p.full_name   as tg_name,
                                              u.club_name
                                       FROM users u
                                                JOIN tg_profiles p ON u.user_id = p.user_id
                                       """)
        rows = await cursor.fetchall()
        return [{"user_id": r[0], "tag": r[1], "name": r[2], "game_role": r[3], "role_status": r[4], "tg_name": r[5],
                 "club_name": r[6]} for r in rows]

    async def is_registered(self, user_id: int) -> bool:
        cursor = await self.db.execute("SELECT 1 FROM tg_profiles WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None

    async def get_user_data(self, user_id: int) -> Optional[tuple]:
        cursor = await self.db.execute("""
                                       SELECT p.user_id, p.full_name, u.bs_tag, p.game_role
                                       FROM tg_profiles p
                                                LEFT JOIN users u ON p.user_id = u.user_id
                                       WHERE p.user_id = ?
                                       """, (user_id,))
        return await cursor.fetchone()

    async def get_user_role(self, user_id: int) -> str:
        cursor = await self.db.execute("SELECT game_role FROM tg_profiles WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else "Гость"

    async def set_user_role(self, user_id: int, role: str, status: str):
        await self.db.execute("UPDATE tg_profiles SET game_role = ?, role_status = ? WHERE user_id = ?",
                              (role, status, user_id))
        await self.db.commit()

    async def register_user(self, user_id: int, tag: str, player_name: str, tg_name: str):
        cursor = await self.db.execute("SELECT user_id FROM tg_profiles WHERE user_id = ?", (user_id,))
        if await cursor.fetchone():
            await self.db.execute(
                "UPDATE tg_profiles SET full_name = ? WHERE user_id = ?",
                (tg_name, user_id)
            )
        else:
            await self.db.execute(
                "INSERT INTO tg_profiles (user_id, full_name, game_role, role_status) VALUES (?, ?, 'Гость', 'Одобрен')",
                (user_id, tg_name)
            )

        cursor2 = await self.db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if await cursor2.fetchone():
            await self.db.execute(
                "UPDATE users SET bs_tag = ?, player_name = ? WHERE user_id = ?",
                (tag, player_name, user_id)
            )
        else:
            await self.db.execute(
                "INSERT INTO users (user_id, bs_tag, player_name) VALUES (?, ?, ?)",
                (user_id, tag, player_name)
            )

        await self.db.commit()