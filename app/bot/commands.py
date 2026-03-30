from __future__ import annotations

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)

from config import settings


BOT_COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="menu", description="Открыть меню"),
    BotCommand(command="add", description="Добавить материал"),
    BotCommand(command="search", description="Поиск материалов"),
    BotCommand(command="web", description="Открыть web-кабинет"),
    BotCommand(command="help", description="Помощь"),
]


async def register_bot_commands(bot: Bot) -> None:
    default_scope = BotCommandScopeDefault()
    private_scope = BotCommandScopeAllPrivateChats()
    admin_chat_scope = BotCommandScopeChat(chat_id=settings.admin_id)

    await bot.delete_my_commands(scope=default_scope)
    await bot.delete_my_commands(scope=private_scope)
    await bot.delete_my_commands(scope=admin_chat_scope)

    await bot.set_my_commands(BOT_COMMANDS, scope=default_scope)
    await bot.set_my_commands(BOT_COMMANDS, scope=private_scope)
    await bot.set_my_commands(BOT_COMMANDS, scope=admin_chat_scope)
