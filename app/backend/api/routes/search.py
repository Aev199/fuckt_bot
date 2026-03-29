from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.api.dependencies import get_current_user
from app.backend.db import crud
from app.backend.db.database import get_session
from app.backend.db.models import User
from app.backend.schemas.material import MaterialListResponse


router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=MaterialListResponse)
async def search_materials(
    q: str = Query(min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MaterialListResponse:
    items, total = await crud.list_materials(
        session=session,
        user_id=user.id,
        q=q,
        limit=limit,
        offset=offset,
    )
    return MaterialListResponse(items=[crud.serialize_material(item) for item in items], total=total)
