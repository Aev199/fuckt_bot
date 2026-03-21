from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from db.crud import get_or_create_user
from db.database import async_session_factory


class DbUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_user = self._extract_telegram_user(event)
        if telegram_user is None:
            return await handler(event, data)

        async with async_session_factory() as session:
            try:
                user = await get_or_create_user(
                    session=session,
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                )
                data["user"] = user
                data["db_session"] = session

                return await handler(event, data)
            except Exception:
                await session.rollback()
                raise

    @staticmethod
    def _extract_telegram_user(event: TelegramObject) -> Any | None:
        if isinstance(event, Message):
            return event.from_user

        if isinstance(event, CallbackQuery):
            return event.from_user

        if isinstance(event, Update):
            if event.message:
                return event.message.from_user
            if event.callback_query:
                return event.callback_query.from_user

        from_user = getattr(event, "from_user", None)
        if from_user is not None:
            return from_user

        return None


def setup_middlewares() -> list[BaseMiddleware]:
    return [DbUserMiddleware()]
