from database.repositories.economy_repo import EconomyRepository
from database.repositories.user_repo import UserRepository
from core.exceptions import NotEnoughMoneyError, UserNotRegisteredError


class EconomyService:
    def __init__(self, eco_repo: EconomyRepository, user_repo: UserRepository):
        self.eco_repo = eco_repo
        self.user_repo = user_repo

    async def get_balance(self, user_id: int) -> int:
        if not await self.user_repo.is_registered(user_id):
            raise UserNotRegisteredError("Пользователь не зарегистрирован.")
        data = await self.eco_repo.get_eco_data(user_id)
        return data.get("balance", 0) if data else 0

    async def transfer(self, from_user: int, to_user: int, amount: int):
        if amount <= 0:
            raise ValueError("Сумма перевода должна быть больше нуля.")
        if not await self.user_repo.is_registered(from_user):
            raise UserNotRegisteredError("Вы не зарегистрированы.")
        if not await self.user_repo.is_registered(to_user):
            raise UserNotRegisteredError("Получатель не зарегистрирован.")

        balance = await self.get_balance(from_user)
        if balance < amount:
            raise NotEnoughMoneyError("Недостаточно средств на балансе.")

        await self.eco_repo.update_balance(from_user, -amount)
        await self.eco_repo.update_balance(to_user, amount)

    async def add_money(self, user_id: int, amount: int):
        if not await self.user_repo.is_registered(user_id):
            raise UserNotRegisteredError("Пользователь не зарегистрирован.")
        await self.eco_repo.update_balance(user_id, amount)