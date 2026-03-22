from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import build_start_session_keyboard
from config import settings
from db import crud
from db.database import async_session_factory


logger = logging.getLogger(__name__)


async def run_reminders(bot: Bot) -> None:
    now_utc = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        users = await crud.get_users_with_notifications_enabled(session=session)

        if not users:
            logger.debug("No users with enabled reminders")
            return

        logger.info("Preparing reminders for %s users", len(users))

        for user in users:
            if not _should_send_reminder(user=user, now_utc=now_utc):
                continue

            await _notify_user(bot=bot, session=session, user_id=user.id, telegram_id=user.telegram_id)


async def _notify_user(
    bot: Bot,
    session: AsyncSession,
    user_id: int,
    telegram_id: int,
) -> None:
    due_cards_count = await crud.count_due_cards(session=session, user_id=user_id)

    try:
        if due_cards_count > 0:
            await bot.send_message(
                chat_id=telegram_id,
                text=f"У тебя {due_cards_count} карточек на повторение!",
                reply_markup=build_start_session_keyboard(review_only=True),
            )
        else:
            await bot.send_message(
                chat_id=telegram_id,
                text="Самое время узнать что-то новое!",
                reply_markup=build_start_session_keyboard(),
            )
    except Exception:
        logger.exception("Failed to send reminder to telegram_id=%s", telegram_id)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
    scheduler.add_job(
        run_reminders,
        trigger="cron",
        minute=0,
        kwargs={"bot": bot},
        id="hourly_reminders",
        replace_existing=True,
    )
    return scheduler


def _should_send_reminder(user, now_utc: datetime) -> bool:
    if not user.notifications_enabled or user.notify_hour is None or not user.timezone:
        return False

    try:
        user_local_hour = now_utc.astimezone(ZoneInfo(user.timezone)).hour
    except Exception:
        logger.exception("Invalid timezone for user_id=%s: %s", user.id, user.timezone)
        return False

    return user_local_hour == user.notify_hour
