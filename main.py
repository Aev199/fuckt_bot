from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.commands import register_bot_commands
from bot.handlers.admin import router as admin_router
from bot.handlers.errors import router as errors_router
from bot.handlers.notifications import router as notifications_router
from bot.handlers.session import router as session_router
from bot.handlers.start import router as start_router
from bot.handlers.stats import router as stats_router
from bot.middlewares import setup_middlewares
from config import settings
from scheduler import setup_scheduler


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())

    for middleware in setup_middlewares():
        dispatcher.update.outer_middleware(middleware)

    dispatcher.include_router(start_router)
    dispatcher.include_router(session_router)
    dispatcher.include_router(stats_router)
    dispatcher.include_router(notifications_router)
    dispatcher.include_router(admin_router)
    dispatcher.include_router(errors_router)

    return dispatcher


async def main() -> None:
    configure_logging()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=settings.bot_parse_mode),
    )
    dispatcher = create_dispatcher()
    scheduler = setup_scheduler(bot)

    await register_bot_commands(bot)
    scheduler.start()
    logging.getLogger(__name__).info("Scheduler started")

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Bot stopped")
