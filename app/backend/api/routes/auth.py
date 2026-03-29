from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.db import crud
from app.backend.db.database import get_session
from app.backend.schemas.common import TelegramAuthRequest
from app.backend.services.telegram_auth import validate_init_data


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/telegram")
async def auth_via_telegram(
    payload: TelegramAuthRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    telegram_user = validate_init_data(payload.init_data)
    user = await crud.get_or_create_user(
        session=session,
        telegram_id=telegram_user.telegram_id,
        username=telegram_user.username,
    )
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
    }
