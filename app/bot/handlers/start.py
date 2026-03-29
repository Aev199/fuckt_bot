from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards import build_start_keyboard


router = Router(name="mini-app-start")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "База знаний по геотехнике готова.\n\n"
        "Открывай Mini App, сохраняй полезные материалы и находи их через категории и поиск.",
        reply_markup=build_start_keyboard(),
    )
