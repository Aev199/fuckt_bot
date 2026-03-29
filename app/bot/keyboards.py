from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config import settings


def build_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть базу знаний",
                    web_app=WebAppInfo(url=settings.mini_app_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Добавить материал",
                    web_app=WebAppInfo(url=f"{settings.mini_app_url}?view=add"),
                )
            ],
        ]
    )
