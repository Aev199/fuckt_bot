from __future__ import annotations

import logging
import traceback

from aiogram import Bot, Router
from aiogram.types import ErrorEvent, Message, Update

from config import settings


logger = logging.getLogger(__name__)

router = Router(name="errors")

_GENERIC_ERROR_TEXT = "Что-то пошло не так. Попробуй ещё раз чуть позже."


@router.error()
async def handle_error(event: ErrorEvent, bot: Bot) -> bool:
    logger.exception("Unhandled bot exception", exc_info=event.exception)

    update = event.update
    await _try_answer_user(update)
    await _try_notify_admin(bot=bot, update=update, exception=event.exception)
    return True


async def _try_answer_user(update: Update) -> None:
    message = _extract_reply_message(update)
    if message is None:
        return

    try:
        await message.answer(_GENERIC_ERROR_TEXT)
    except Exception:
        logger.exception("Failed to send generic error response to user")


async def _try_notify_admin(bot: Bot, update: Update, exception: Exception) -> None:
    user_id = _extract_user_id(update)
    update_type = _detect_update_type(update)
    short_trace = "".join(traceback.format_exception_only(type(exception), exception)).strip()

    text = (
        "Bot error\n"
        f"Type: {type(exception).__name__}\n"
        f"Update: {update_type}\n"
        f"User: {user_id or 'unknown'}\n"
        f"Details: {short_trace[:800]}"
    )

    try:
        await bot.send_message(chat_id=settings.admin_id, text=text)
    except Exception:
        logger.exception("Failed to notify admin about bot error")


def _extract_reply_message(update: Update) -> Message | None:
    if update.message:
        return update.message
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return None


def _extract_user_id(update: Update) -> int | None:
    if update.message and update.message.from_user:
        return update.message.from_user.id
    if update.callback_query and update.callback_query.from_user:
        return update.callback_query.from_user.id
    return None


def _detect_update_type(update: Update) -> str:
    if update.message:
        return "message"
    if update.callback_query:
        return "callback_query"
    return "unknown"
