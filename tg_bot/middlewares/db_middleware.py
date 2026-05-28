import aiosqlite
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from core.config import settings
from database.repositories.economy_repo import EconomyRepository
from database.repositories.user_repo import UserRepository
from database.repositories.chat_repo import ChatRepository
from services.economy_service import EconomyService
from services.ai_service import AiService
from services.casino_service import CasinoService
from services.registration_service import RegistrationService
from external.groq_client import GroqClient
from external.brawl_api import BrawlAPIClient

class ServicesMiddleware(BaseMiddleware):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.groq_client = GroqClient()
        self.brawl_client = BrawlAPIClient()

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        async with aiosqlite.connect(self.db_path) as db:
            eco_repo = EconomyRepository(db)
            user_repo = UserRepository(db)
            chat_repo = ChatRepository(db)
            eco_service = EconomyService(eco_repo, user_repo)
            ai_service = AiService(chat_repo, self.groq_client)
            casino_service = CasinoService(eco_repo)
            reg_service = RegistrationService(user_repo, self.brawl_client)
            data["eco_repo"] = eco_repo
            data["user_repo"] = user_repo
            data["chat_repo"] = chat_repo
            data["eco_service"] = eco_service
            data["ai_service"] = ai_service
            data["casino_service"] = casino_service
            data["reg_service"] = reg_service
            data["brawl_client"] = self.brawl_client
            return await handler(event, data)