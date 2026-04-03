from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.db import crud
from app.backend.db.database import get_session
from app.backend.db.models import User
from app.backend.services.telegram_auth import validate_init_data
from config import settings


async def get_current_user(
    x_telegram_init_data: Annotated[str | None, Header()] = None,
    x_web_cabinet_token: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    if x_telegram_init_data:
        telegram_user = validate_init_data(x_telegram_init_data)
        return await crud.get_or_create_user(
            session=session,
            telegram_id=telegram_user.telegram_id,
            username=telegram_user.username,
        )

    if settings.web_cabinet_token and x_web_cabinet_token == settings.web_cabinet_token:
        return await crud.get_or_create_user(
            session=session,
            telegram_id=settings.admin_id,
            username="admin",
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing valid auth header")


async def get_current_user_for_media(
    init_data: Annotated[str | None, Query()] = None,
    token: Annotated[str | None, Query()] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    if init_data:
        telegram_user = validate_init_data(init_data)
        return await crud.get_or_create_user(
            session=session,
            telegram_id=telegram_user.telegram_id,
            username=telegram_user.username,
        )

    if settings.web_cabinet_token and token == settings.web_cabinet_token:
        return await crud.get_or_create_user(
            session=session,
            telegram_id=settings.admin_id,
            username="admin",
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing valid media auth")


def can_edit_web(user: User) -> bool:
    return user.telegram_id in settings.web_editor_telegram_ids


async def require_web_editor(user: User = Depends(get_current_user)) -> User:
    if not can_edit_web(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Editing is not allowed for this user")
    return user
