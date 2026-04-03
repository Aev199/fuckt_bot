from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.api.dependencies import get_current_user, require_web_editor
from app.backend.db import crud
from app.backend.db.database import get_session
from app.backend.db.models import User
from app.backend.schemas.category import CategoryCreate


router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("")
async def get_categories(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await crud.list_categories(session=session, user_id=user.id)


@router.post("")
async def post_category(
    payload: CategoryCreate,
    user: User = Depends(require_web_editor),
    session: AsyncSession = Depends(get_session),
) -> dict:
    category = await crud.create_category(session=session, user_id=user.id, payload=payload)
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "parent_id": category.parent_id,
        "created_at": category.created_at,
        "materials_count": 0,
    }
