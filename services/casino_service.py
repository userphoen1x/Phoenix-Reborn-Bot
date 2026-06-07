from database.repositories.economy_repo import EconomyRepository
from database.repositories.user_repo import UserRepository
from database.repositories.game_repo import GameRepository
from core.exceptions import NotEnoughMoneyError, UserNotRegisteredError
from typing import Optional

class CasinoService:
    def __init__(self, eco_repo: EconomyRepository, user_repo: UserRepository, game_repo: GameRepository):
        self.eco_repo = eco_repo
        self.user_repo = user_repo
        self.game_repo = game_repo

    async def get_balance(self, user_id: int) -> int:
        eco = await self.eco_repo.get_eco_data(user_id)
        if not eco or not eco.get("bs_tag"): raise UserNotRegisteredError()
        return eco["balance"]

    async def charge_bet(self, user_id: int, bet: int) -> int:
        eco = await self.eco_repo.get_eco_data(user_id)
        if not eco or not eco.get("bs_tag"): raise UserNotRegisteredError()
        if eco["balance"] < bet: raise NotEnoughMoneyError()
        await self.eco_repo.update_balance(user_id, -bet)
        return eco["balance"] - bet

    async def credit_win(self, user_id: int, amount: int):
        if amount > 0:
            await self.eco_repo.update_balance(user_id, amount)

    async def play_emoji_game(self, user_id: int, game: str, bet: int, dice_value: int, guess: int = None) -> tuple:
        await self.charge_bet(user_id, bet)
        mult = 0.0
        msg_result = "Увы, ставка сгорела. 😔"
        if game == "slot":
            if dice_value == 64: mult, msg_result = 10.0, "ДЖЕКПОТ! 777! 🎉 (x10)"
            elif dice_value in [1, 22, 43]: mult, msg_result = 5.0, "Три в ряд! Отличный куш! 🍒 (x5)"
        elif game == "dice":
            if dice_value == guess: mult, msg_result = 5.0, f"Угадал! Выпало {dice_value}! 🎲🎉 (x5)"
            else: msg_result = f"Мимо. Выпало {dice_value}, а ты ставил на {guess}. 😔"
        elif game in ["darts", "bowl"]:
            if dice_value == 6: mult, msg_result = 3.0, "Прямо в цель! Идеально! 🏆 (x3)"
        elif game in ["fball", "bball"]:
            if dice_value in [4, 5]: mult, msg_result = 2.0, "ГООООЛ! / Точно в корзину! 🏆 (x2)"
        win_amount = int(bet * mult)
        await self.credit_win(user_id, win_amount)
        return msg_result, win_amount

    async def save_active_game(self, user_id: int, game_type: str, state: dict):
        await self.game_repo.save_game(user_id, game_type, state)

    async def get_active_game(self, user_id: int) -> Optional[dict]:
        return await self.game_repo.get_game(user_id)

    async def delete_active_game(self, user_id: int):
        await self.game_repo.delete_game(user_id)