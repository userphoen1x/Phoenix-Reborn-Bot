import aiosqlite
from datetime import datetime, date, timedelta
from typing import List, Tuple, Dict

class ChatRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def log_chat_message(self, chat_id: int, user_id: int, full_name: str, text: str):
        await self.db.execute("INSERT INTO chat_logs (chat_id, user_id, full_name, text, msg_timestamp) VALUES (?, ?, ?, ?, ?)", (chat_id, user_id, full_name, text, datetime.now().isoformat()))
        await self.db.commit()

    async def get_chat_context(self, chat_id: int, limit: int = 15) -> List[Tuple]:
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        query = "SELECT user_id, full_name, text FROM chat_logs WHERE chat_id = ? AND msg_timestamp >= ? ORDER BY msg_timestamp DESC LIMIT ?"
        async with self.db.execute(query, (chat_id, three_days_ago, limit)) as cursor:
            rows = await cursor.fetchall()
            return rows[::-1]

    async def get_today_chat_logs(self, chat_id: int) -> str:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        query = "SELECT full_name, text FROM chat_logs WHERE chat_id = ? AND msg_timestamp >= ? ORDER BY msg_timestamp ASC"
        async with self.db.execute(query, (chat_id, today_start)) as cursor:
            rows = await cursor.fetchall()
            return "\n".join([f"{row[0]}: {row[1]}" for row in rows])

    async def get_chat_mode(self, chat_id: int) -> str:
        async with self.db.execute("SELECT mode FROM chat_modes WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "default"

    async def set_chat_mode(self, chat_id: int, mode: str):
        await self.db.execute("INSERT OR REPLACE INTO chat_modes (chat_id, mode) VALUES (?, ?)", (chat_id, mode))
        await self.db.commit()

    async def clear_old_chat_logs(self):
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        await self.db.execute("DELETE FROM chat_logs WHERE msg_timestamp < ?", (three_days_ago,))
        await self.db.commit()

    async def clear_chat_logs(self, chat_id: int):
        await self.db.execute("DELETE FROM chat_logs WHERE chat_id = ?", (chat_id,))
        await self.db.commit()

    async def increment_message(self, user_id: int, chat_id: int, full_name: str):
        today = date.today().isoformat()
        await self.db.execute("INSERT OR IGNORE INTO tg_profiles (user_id, full_name) VALUES (?, ?)", (user_id, full_name))
        await self.db.execute("INSERT INTO messages (user_id, chat_id, msg_date, msg_count) VALUES (?, ?, ?, 1) ON CONFLICT(user_id, chat_id, msg_date) DO UPDATE SET msg_count = msg_count + 1", (user_id, chat_id, today))
        await self.db.commit()

    async def get_top_messages(self, days: int = None) -> List[Tuple]:
        query = "SELECT t.full_name, u.player_name, SUM(m.msg_count) as total, m.user_id FROM messages m LEFT JOIN tg_profiles t ON m.user_id = t.user_id LEFT JOIN users u ON m.user_id = u.user_id"
        params = []
        if days is not None:
            td = (date.today() - timedelta(days=days)).isoformat()
            query += " WHERE m.msg_date >= ? "
            params.append(td)
        query += " GROUP BY m.user_id ORDER BY total DESC LIMIT 10"
        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def save_snapshot(self, tag: str, name: str, dt: str, trophies: int, solo: int, duo: int, wins3v3: int, rank_c: int, rank_h: int):
        await self.db.execute("INSERT OR REPLACE INTO bs_snapshots (tag, name, record_date, trophies, solo_wins, duo_wins, wins_3v3, rank_current, rank_highest) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (tag, name, dt, trophies, solo, duo, wins3v3, rank_c, rank_h))
        await self.db.commit()

    async def get_baseline_trophies(self, days: int, tags_filter: List[str] = None) -> Dict[str, int]:
        if tags_filter is not None and len(tags_filter) == 0: return {}
        logical_today = datetime.now().date()
        td = (logical_today - timedelta(days=days - 1)).isoformat()
        query = "SELECT tag, trophies FROM bs_snapshots s1 WHERE record_date = (SELECT MIN(record_date) FROM bs_snapshots s2 WHERE s2.tag = s1.tag AND s2.record_date >= ?)"
        params = [td]
        if tags_filter:
            placeholders = ",".join("?" for _ in tags_filter)
            query += f" AND s1.tag IN ({placeholders})"
            params.extend(tags_filter)
        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}