from database.repositories.economy_repo import EconomyRepository
from core.exceptions import NotEnoughMoneyError, UserNotRegisteredError

class CasinoService:
    def __init__(self, eco_repo: EconomyRepository):
        self.eco_repo = eco_repo
        self.last_game_msgs = {}
        self.bj_games = {}
        self.saper_games = {}

    async def _check_and_charge_bet(self, user_id: int, bet: int) -> int:
        eco = await self.eco_repo.get_eco_data(user_id)
        if not eco or not eco.get("bs_tag"): raise UserNotRegisteredError()
        if eco["balance"] < bet: raise NotEnoughMoneyError()
        await self.eco_repo.update_balance(user_id, -bet)
        return eco["balance"]

    async def play_emoji_game(self, user_id: int, game: str, bet: int, dice_value: int, guess: int = None) -> tuple:
        await self._check_and_charge_bet(user_id, bet)
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
        if win_amount > 0:
            await self.eco_repo.update_balance(user_id, win_amount)
        return msg_result, win_amount