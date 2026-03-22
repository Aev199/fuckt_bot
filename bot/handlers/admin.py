from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db import crud
from db.models import Card, User


router = Router(name="admin")


@router.message(Command("health"))
async def cmd_health(
    message: Message,
    db_session: AsyncSession,
    user: User,
) -> None:
    if not _is_admin(user):
        await message.answer("Эта команда доступна только администратору.")
        return

    active_cards = (
        await db_session.execute(
            select(func.count(Card.id)).where(Card.active.is_(True))
        )
    ).scalar_one()
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    await message.answer(
        "OK\n"
        f"UTC time: {now_utc}\n"
        "DB connectivity: confirmed\n"
        f"Active cards: {active_cards}"
    )


@router.message(Command("admin_stats"))
async def cmd_admin_stats(
    message: Message,
    db_session: AsyncSession,
    user: User,
) -> None:
    if not _is_admin(user):
        await message.answer("Эта команда доступна только администратору.")
        return

    stats = await crud.get_admin_stats(session=db_session)
    await message.answer(
        "Admin stats:\n\n"
        f"Users total: {stats['total_users']}\n"
        f"Users with progress: {stats['users_with_progress']}\n"
        f"Users with reminders: {stats['reminders_enabled']}\n"
        f"Active cards: {stats['active_cards']}\n"
        f"Active topics: {stats['active_topics']}\n"
        f"Due reviews total: {stats['due_reviews_total']}"
    )


def _is_admin(user: User) -> bool:
    return user.telegram_id == settings.admin_id
