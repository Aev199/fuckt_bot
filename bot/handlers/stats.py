from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from db.models import User


router = Router(name="stats")


@router.message(Command("stats"))
async def cmd_stats(
    message: Message,
    db_session: AsyncSession,
    user: User,
) -> None:
    stats = await crud.get_user_stats(session=db_session, user_id=user.id)

    await message.answer(
        "Твоя статистика:\n\n"
        f"Просмотрено карточек: {stats['total_seen']}\n"
        f"Знал: {stats['knew']}\n"
        f"Сомневался: {stats['unsure']}\n"
        f"Не знал: {stats['didnt']}\n"
        f"На повторение сейчас: {stats['due_now']}"
    )
