import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import ActiveGame

class GameRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def init_table(self):
        pass

    async def save_game(self, user_id: int, game_type: str, state: dict):
        state_str = json.dumps(state, ensure_ascii=False)
        game = await self.session.get(ActiveGame, user_id)
        if game:
            game.game_type = game_type
            game.state_json = state_str
        else:
            game = ActiveGame(user_id=user_id, game_type=game_type, state_json=state_str)
            self.session.add(game)
        await self.session.commit()

    async def get_game(self, user_id: int) -> Optional[dict]:
        game = await self.session.get(ActiveGame, user_id)
        if game:
            return {"game_type": game.game_type, "state": json.loads(game.state_json)}
        return None

    async def delete_game(self, user_id: int):
        game = await self.session.get(ActiveGame, user_id)
        if game:
            await self.session.delete(game)
            await self.session.commit()