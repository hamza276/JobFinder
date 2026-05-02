from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db as _get_db


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in _get_db():
        yield session
