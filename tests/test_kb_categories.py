from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.backend.db import crud
from app.backend.db.database import Base
from app.backend.schemas.category import CategoryCreate
from app.backend.schemas.material import MaterialCreate


@pytest.fixture()
async def kb_category_session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    db_path = tmp_path / "kb_categories.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, class_=AsyncSession)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_category_tree_allows_only_one_level(kb_category_session_factory) -> None:
    async with kb_category_session_factory() as session:
        user = await crud.get_or_create_user(session=session, telegram_id=2001, username="treeuser")
        root = await crud.create_category(session=session, user_id=user.id, payload=CategoryCreate(name="Грунты"))
        child = await crud.create_category(
            session=session,
            user_id=user.id,
            payload=CategoryCreate(name="Суглинки", parent_id=root.id),
        )

        with pytest.raises(ValueError, match="Only one level of subcategories is allowed"):
            await crud.create_category(
                session=session,
                user_id=user.id,
                payload=CategoryCreate(name="Глинистые", parent_id=child.id),
            )


@pytest.mark.asyncio
async def test_list_materials_by_top_category_includes_subcategories(kb_category_session_factory) -> None:
    async with kb_category_session_factory() as session:
        user = await crud.get_or_create_user(session=session, telegram_id=2002, username="filteruser")
        root = await crud.create_category(session=session, user_id=user.id, payload=CategoryCreate(name="Грунты"))
        child = await crud.create_category(
            session=session,
            user_id=user.id,
            payload=CategoryCreate(name="Суглинки", parent_id=root.id),
        )
        other = await crud.create_category(session=session, user_id=user.id, payload=CategoryCreate(name="Фундаменты"))

        await crud.create_material(
            session=session,
            user_id=user.id,
            payload=MaterialCreate(title="Общий материал", content="Root", category_id=root.id, tags=[]),
        )
        await crud.create_material(
            session=session,
            user_id=user.id,
            payload=MaterialCreate(title="Подкатегория", content="Child", category_id=child.id, tags=[]),
        )
        await crud.create_material(
            session=session,
            user_id=user.id,
            payload=MaterialCreate(title="Другое", content="Other", category_id=other.id, tags=[]),
        )

        items, total = await crud.list_materials(session=session, user_id=user.id, top_category_id=root.id)

        assert total == 2
        assert {item.title for item in items} == {"Общий материал", "Подкатегория"}
