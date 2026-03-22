from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.database import Base


@pytest.fixture()
async def session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, class_=AsyncSession)
    try:
        yield factory
    finally:
        await engine.dispose()
