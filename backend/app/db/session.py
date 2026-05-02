from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base


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
    """Create tables for local Phase 1 development.

    Alembic can replace this in production, but the scaffold currently ships
    without migrations.
    """
    import app.models.email_draft  # noqa: F401
    import app.models.job  # noqa: F401
    import app.models.profile  # noqa: F401
    import app.models.scan_log  # noqa: F401
    import app.models.user  # noqa: F401

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


@asynccontextmanager
async def get_db_context() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
