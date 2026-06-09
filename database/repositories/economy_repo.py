from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database.models import Economy, User

class EconomyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_eco_data(self, user_id: int) -> Optional[dict]:
        eco = await self.session.get(Economy, user_id)
        if eco:
            return {"balance": eco.balance, "bs_tag": eco.bs_tag, "last_daily": eco.last_daily}
        return None

    async def update_balance(self, user_id: int, amount: int):
        eco = await self.session.get(Economy, user_id)
        if eco:
            eco.balance += amount
            await self.session.commit()

    async def get_top_balance(self, limit: int = 10) -> List[Tuple[str, str, int, int]]:
        stmt = (
            select(User.tg_name, User.name, Economy.balance, User.user_id)
            .outerjoin(User, Economy.user_id == User.user_id)
            .order_by(desc(Economy.balance))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [(row.tg_name, row.name, row.balance, row.user_id) for row in result]

    async def update_last_daily(self, user_id: int, date_str: str):
        eco = await self.session.get(Economy, user_id)
        if eco:
            eco.last_daily = date_str
            await self.session.commit()