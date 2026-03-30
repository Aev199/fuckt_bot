from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.backend.db import crud
from app.backend.db.database import Base
from app.backend.schemas.material import MaterialCreate


@pytest.fixture()
async def kb_session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    db_path = tmp_path / "kb_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, class_=AsyncSession)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_material_attachment_roundtrip(kb_session_factory) -> None:
    async with kb_session_factory() as session:
        user = await crud.get_or_create_user(session=session, telegram_id=999, username="tester")
        material = await crud.create_material(
            session=session,
            user_id=user.id,
            payload=MaterialCreate(
                title="Soil profile",
                content="Layer description",
                tags=["soil"],
            ),
        )

        attachment = await crud.add_material_attachment(
            session=session,
            user_id=user.id,
            material_id=material.id,
            telegram_file_id="file_123",
            file_path="photos/file_123.jpg",
            file_name="profile.jpg",
            mime_type="image/jpeg",
            caption="Схема разреза",
        )

        loaded_material = await crud.get_material(session=session, user_id=user.id, material_id=material.id)
        serialized = crud.serialize_material(loaded_material)

        assert len(serialized.attachments) == 1
        assert serialized.attachments[0].id == attachment.id
        assert serialized.attachments[0].caption == "Схема разреза"


@pytest.mark.asyncio
async def test_delete_material_attachment_reorders_remaining_items(kb_session_factory) -> None:
    async with kb_session_factory() as session:
        user = await crud.get_or_create_user(session=session, telegram_id=1000, username="tester2")
        material = await crud.create_material(
            session=session,
            user_id=user.id,
            payload=MaterialCreate(
                title="Foundation detail",
                content="Important notes",
                tags=[],
            ),
        )

        first = await crud.add_material_attachment(
            session=session,
            user_id=user.id,
            material_id=material.id,
            telegram_file_id="file_1",
            file_path="photos/file_1.jpg",
        )
        second = await crud.add_material_attachment(
            session=session,
            user_id=user.id,
            material_id=material.id,
            telegram_file_id="file_2",
            file_path="photos/file_2.jpg",
        )

        await crud.delete_material_attachment(
            session=session,
            user_id=user.id,
            material_id=material.id,
            attachment_id=first.id,
        )

        loaded_material = await crud.get_material(session=session, user_id=user.id, material_id=material.id)
        assert len(loaded_material.attachments) == 1
        assert loaded_material.attachments[0].id == second.id
        assert loaded_material.attachments[0].sort_order == 0
