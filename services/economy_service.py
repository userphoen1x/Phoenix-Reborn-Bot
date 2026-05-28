import random
from datetime import datetime, timedelta
from database.repositories.economy_repo import EconomyRepository
from database.repositories.user_repo import UserRepository
from core.exceptions import UserNotRegisteredError, WorkCooldownError, NotEnoughMoneyError

class EconomyService:
    def __init__(self, eco_repo: EconomyRepository, user_repo: UserRepository):
        self.eco_repo = eco_repo
        self.user_repo = user_repo

    def get_class_bonus(self, bot_class: str) -> dict:
        if bot_class == "Махим": return {"work_cd": 4, "luck": 0.10, "rob_mult": 1.0}
        if bot_class == "Спырту": return {"work_cd": 3, "luck": -0.05, "rob_mult": 1.5}
        if bot_class == "Ванёк": return {"work_cd": 5, "luck": 0.20, "rob_mult": 1.0}
        return {"work_cd": 4, "luck": 0.0, "rob_mult": 1.0}

    async def get_balance(self, user_id: int) -> int:
        eco = await self.eco_repo.get_eco_data(user_id)
        if not eco or not eco.get("bs_tag"): raise UserNotRegisteredError()
        return eco["balance"]

    async def do_work(self, user_id: int) -> int:
        eco = await self.eco_repo.get_eco_data(user_id)
        if not eco or not eco.get("bs_tag"): raise UserNotRegisteredError()
        bonuses = self.get_class_bonus(eco["bot_class"])
        cd_hours = bonuses["work_cd"]
        now = datetime.now()
        if eco["last_work"]:
            last_work = datetime.fromisoformat(eco["last_work"])
            diff = now - last_work
            if diff < timedelta(hours=cd_hours):
                rem = timedelta(hours=cd_hours) - diff
                mm, ss = divmod(int(rem.total_seconds()), 60)
                hh, mm = divmod(mm, 60)
                raise WorkCooldownError(hours=hh, minutes=mm)
        reward = random.randint(50, 150)
        await self.eco_repo.update_balance(user_id, reward)
        await self.eco_repo.set_eco_data(user_id, "last_work", now.isoformat())
        return reward

    async def transfer_funds(self, sender_id: int, target_id: int, amount: int) -> None:
        if amount <= 0: raise ValueError("Сумма перевода должна быть больше нуля.")
        if sender_id == target_id: raise ValueError("Нельзя переводить Феники самому себе.")
        eco_sender = await self.eco_repo.get_eco_data(sender_id)
        if not eco_sender or not eco_sender.get("bs_tag"): raise UserNotRegisteredError("Вы не зарегистрированы!")
        if eco_sender["balance"] < amount: raise NotEnoughMoneyError()
        eco_target = await self.eco_repo.get_eco_data(target_id)
        if not eco_target or not eco_target.get("bs_tag"): raise UserNotRegisteredError("Этот пользователь еще не зарегистрирован.")
        await self.eco_repo.update_balance(sender_id, -amount)
        await self.eco_repo.update_balance(target_id, amount)