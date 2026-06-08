import aiosqlite
from typing import AsyncIterable
from dishka import Provider, Scope, provide

from core.config import settings
from database.repositories.user_repo import UserRepository
from database.repositories.chat_repo import ChatRepository
from database.repositories.economy_repo import EconomyRepository
from database.repositories.game_repo import GameRepository
from services.economy_service import EconomyService
from services.casino_service import CasinoService
from services.ai_service import AiService
from external.brawl_api import BrawlAPIClient
from external.groq_client import GroqClient

class AppProvider(Provider):
    # Открываем соединение с БД на каждый запрос от Telegram
    @provide(scope=Scope.REQUEST)
    async def get_db(self) -> AsyncIterable[aiosqlite.Connection]:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            yield db

    # Внешние API (живут все время работы бота)
    @provide(scope=Scope.APP)
    def get_brawl_client(self) -> BrawlAPIClient:
        return BrawlAPIClient()

    @provide(scope=Scope.APP)
    def get_groq_client(self) -> GroqClient:
        return GroqClient()

    # Репозитории собираются автоматически, запрашивая get_db()
    user_repo = provide(UserRepository, scope=Scope.REQUEST)
    chat_repo = provide(ChatRepository, scope=Scope.REQUEST)
    eco_repo = provide(EconomyRepository, scope=Scope.REQUEST)
    game_repo = provide(GameRepository, scope=Scope.REQUEST)

    # Сервисы собираются автоматически, запрашивая репозитории
    eco_service = provide(EconomyService, scope=Scope.REQUEST)
    casino_service = provide(CasinoService, scope=Scope.REQUEST)
    ai_service = provide(AiService, scope=Scope.REQUEST)