from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from core.config import settings
from database.models import Base

engine = create_async_engine(f"sqlite+aiosqlite:///{settings.DB_PATH}", echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)