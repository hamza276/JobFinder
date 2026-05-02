from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


engine = None
AsyncSessionLocal = None


def get_engine():
    global engine
    if engine is None:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
        )
    return engine


def get_sessionmaker():
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return AsyncSessionLocal


async def init_db() -> None:
    """Validate database connectivity.

    Schema changes are managed through Alembic migrations.
    """
    async with get_engine().begin() as conn:
        await conn.execute(text("SELECT 1"))


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


@asynccontextmanager
async def get_db_context() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
