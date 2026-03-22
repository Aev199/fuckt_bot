from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat

from config import settings


USER_COMMANDS = [
    BotCommand(command="start", description="Запуск и выбор темы"),
    BotCommand(command="session", description="Начать сессию"),
    BotCommand(command="stats", description="Личная статистика"),
    BotCommand(command="remind", description="Настроить напоминания"),
    BotCommand(command="help", description="Помощь"),
]

ADMIN_COMMANDS = [
    *USER_COMMANDS,
    BotCommand(command="health", description="Проверка состояния бота"),
    BotCommand(command="admin_stats", description="Админская статистика"),
]


async def register_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        USER_COMMANDS,
        scope=BotCommandScopeAllPrivateChats(),
    )
    await bot.set_my_commands(
        ADMIN_COMMANDS,
        scope=BotCommandScopeChat(chat_id=settings.admin_id),
    )
