from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import config

from .partitions import insert_partitions

from .models import Base

engine = create_async_engine(
    config.DB_URI.get_secret_value(),
    echo=True,
)


SessionMaker = async_sessionmaker(bind=engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionMaker() as session:
        yield session
