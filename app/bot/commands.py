from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats


BOT_COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="menu", description="Открыть меню"),
    BotCommand(command="add", description="Добавить материал"),
    BotCommand(command="search", description="Поиск материалов"),
    BotCommand(command="web", description="Открыть web-кабинет"),
    BotCommand(command="help", description="Помощь"),
]


async def register_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllPrivateChats())
