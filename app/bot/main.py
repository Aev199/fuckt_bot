from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.commands import register_bot_commands
from app.bot.handlers.knowledge import router as knowledge_router
from app.bot.middlewares import DbUserMiddleware
from config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.outer_middleware(DbUserMiddleware())
    dispatcher.include_router(knowledge_router)
    return dispatcher


async def main() -> None:
    configure_logging()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=settings.bot_parse_mode),
    )
    dispatcher = create_dispatcher()

    try:
        await register_bot_commands(bot)
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
