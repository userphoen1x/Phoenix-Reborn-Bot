from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from database.models import Economy, User


class EconomyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_eco_data(self, user_id: int) -> Optional[dict]:
        stmt = select(User.bs_tag, Economy.balance, Economy.last_daily) \
            .outerjoin(Economy, User.user_id == Economy.user_id) \
            .where(User.user_id == user_id)

        result = await self.session.execute(stmt)
        row = result.first()

        if row:
            return {
                "bs_tag": row[0],
                "balance": row[1] if row[1] is not None else 0,
                "last_daily": row[2]
            }
        return None

    async def update_balance(self, user_id: int, amount: int):
        eco = await self.session.get(Economy, user_id)
        if eco:
            eco.balance += amount
        else:
            eco = Economy(user_id=user_id, balance=amount)
            self.session.add(eco)
        await self.session.commit()

    async def get_top_balance(self, limit: int = 10) -> List[Tuple[str, str, int, int]]:
        query = """
                SELECT p.full_name, u.player_name, e.balance, e.user_id
                FROM economy e
                         LEFT JOIN tg_profiles p ON e.user_id = p.user_id
                         LEFT JOIN users u ON e.user_id = u.user_id
                ORDER BY e.balance DESC LIMIT :limit \
                """
        result = await self.session.execute(text(query), {"limit": limit})
        return [(row[0], row[1], row[2], row[3]) for row in result]

    async def update_last_daily(self, user_id: int, date_str: str):
        eco = await self.session.get(Economy, user_id)
        if eco:
            eco.last_daily = date_str
        else:
            eco = Economy(user_id=user_id, balance=0, last_daily=date_str)
            self.session.add(eco)
        await self.session.commit()