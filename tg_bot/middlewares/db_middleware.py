import aiosqlite
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from database.repositories.user_repo import UserRepository
from database.repositories.chat_repo import ChatRepository
from database.repositories.economy_repo import EconomyRepository
from database.repositories.game_repo import GameRepository
from external.brawl_api import BrawlAPIClient
from external.groq_client import GroqClient
from services.economy_service import EconomyService
from services.casino_service import CasinoService
from services.ai_service import AiService

class DBMiddleware(BaseMiddleware):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.brawl_client = BrawlAPIClient()
        self.groq_client = GroqClient()
        self.tables_initialized = False

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        async with aiosqlite.connect(self.db_path) as db:
            user_repo = UserRepository(db)
            chat_repo = ChatRepository(db)
            eco_repo = EconomyRepository(db)
            game_repo = GameRepository(db)

            if not self.tables_initialized:
                await game_repo.init_table()
                self.tables_initialized = True

            eco_service = EconomyService(eco_repo, user_repo)
            casino_service = CasinoService(eco_repo, user_repo, game_repo)
            ai_service = AiService(chat_repo, self.groq_client)

            data["user_repo"] = user_repo
            data["chat_repo"] = chat_repo
            data["eco_repo"] = eco_repo
            data["game_repo"] = game_repo
            data["brawl_client"] = self.brawl_client
            data["eco_service"] = eco_service
            data["casino_service"] = casino_service
            data["ai_service"] = ai_service

            return await handler(event, data)