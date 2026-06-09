import aiosqlite
from typing import AsyncIterable
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from database.connection import async_session
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
    # ОСТАВЛЯЕМ старый коннект для непереведенных репозиториев (Chat, User)
    @provide(scope=Scope.REQUEST)
    async def get_db(self) -> AsyncIterable[aiosqlite.Connection]:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            yield db

    # ДОБАВЛЯЕМ новую сессию ORM для переведенных репозиториев (Eco, Game)
    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> AsyncIterable[AsyncSession]:
        async with async_session() as session:
            yield session

    @provide(scope=Scope.APP)
    def get_brawl_client(self) -> BrawlAPIClient:
        return BrawlAPIClient()

    @provide(scope=Scope.APP)
    def get_groq_client(self) -> GroqClient:
        return GroqClient()

    user_repo = provide(UserRepository, scope=Scope.REQUEST)
    chat_repo = provide(ChatRepository, scope=Scope.REQUEST)
    eco_repo = provide(EconomyRepository, scope=Scope.REQUEST)
    game_repo = provide(GameRepository, scope=Scope.REQUEST)

    eco_service = provide(EconomyService, scope=Scope.REQUEST)
    casino_service = provide(CasinoService, scope=Scope.REQUEST)
    ai_service = provide(AiService, scope=Scope.REQUEST)