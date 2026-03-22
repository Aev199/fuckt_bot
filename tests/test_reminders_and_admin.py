from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from bot.commands import ADMIN_COMMANDS, USER_COMMANDS, register_bot_commands
from bot.handlers.admin import _is_admin
from bot.handlers.session import _should_offer_reminder_onboarding
from config import settings
from db.models import User
from scheduler.reminders import _should_send_reminder


@pytest.mark.asyncio
async def test_register_bot_commands_configures_user_and_admin_scopes() -> None:
    bot = AsyncMock()

    await register_bot_commands(bot)

    assert bot.set_my_commands.await_count == 2
    first_call = bot.set_my_commands.await_args_list[0]
    second_call = bot.set_my_commands.await_args_list[1]
    assert list(first_call.args[0]) == USER_COMMANDS
    assert list(second_call.args[0]) == ADMIN_COMMANDS


def test_should_offer_reminder_onboarding_only_after_first_completed_session() -> None:
    user = User(telegram_id=1, username="u", notifications_enabled=False)
    assert _should_offer_reminder_onboarding(user=user, state_data={"session_count": 5, "session_started_total_seen": 0}) is True
    assert _should_offer_reminder_onboarding(user=user, state_data={"session_count": 0, "session_started_total_seen": 0}) is False
    assert _should_offer_reminder_onboarding(user=user, state_data={"session_count": 5, "session_started_total_seen": 3}) is False
    user.notifications_enabled = True
    assert _should_offer_reminder_onboarding(user=user, state_data={"session_count": 5, "session_started_total_seen": 0}) is False


def test_should_send_reminder_uses_user_timezone() -> None:
    user = User(
        telegram_id=2,
        username="tz",
        notifications_enabled=True,
        timezone="Europe/Moscow",
        notify_hour=9,
    )
    assert _should_send_reminder(user=user, now_utc=datetime(2026, 3, 22, 6, 0, tzinfo=timezone.utc)) is True
    assert _should_send_reminder(user=user, now_utc=datetime(2026, 3, 22, 7, 0, tzinfo=timezone.utc)) is False


def test_admin_helper_recognizes_admin_user() -> None:
    admin_user = User(telegram_id=settings.admin_id, username="admin")
    regular_user = User(telegram_id=settings.admin_id + 1, username="user")

    assert _is_admin(admin_user) is True
    assert _is_admin(regular_user) is False
