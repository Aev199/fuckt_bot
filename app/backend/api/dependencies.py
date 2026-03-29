from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.db import crud
from app.backend.db.database import get_session
from app.backend.db.models import User
from app.backend.services.telegram_auth import validate_init_data


async def get_current_user(
    x_telegram_init_data: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    if not x_telegram_init_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Telegram auth header")

    telegram_user = validate_init_data(x_telegram_init_data)
    return await crud.get_or_create_user(
        session=session,
        telegram_id=telegram_user.telegram_id,
        username=telegram_user.username,
    )
