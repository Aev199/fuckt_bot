from __future__ import annotations

from urllib.parse import urlencode

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings


class AppNav(CallbackData, prefix="nav"):
    screen: str
    value: str | None = None


def build_home_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить", callback_data=AppNav(screen="add"))
    builder.button(text="Поиск", callback_data=AppNav(screen="search"))
    builder.button(text="Категории", callback_data=AppNav(screen="categories"))
    builder.button(text="Последние", callback_data=AppNav(screen="recent"))
    builder.button(text="Избранное", callback_data=AppNav(screen="favorites"))
    builder.button(text="Web-кабинет", url=_build_web_cabinet_url())
    builder.adjust(2, 2, 2)
    return builder.as_markup()


def build_back_home_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Назад в меню", callback_data=AppNav(screen="home"))
    return builder.as_markup()


def build_categories_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(
            text=f"{category['name']} ({category['materials_count']})",
            callback_data=AppNav(screen="category", value=str(category["id"])),
        )
    builder.button(text="Новая категория", callback_data=AppNav(screen="new_category"))
    builder.button(text="Назад в меню", callback_data=AppNav(screen="home"))
    builder.adjust(1)
    return builder.as_markup()


def build_materials_keyboard(materials: list, back_screen: str, back_value: str | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for material in materials:
        builder.button(
            text=material.title,
            callback_data=AppNav(screen="material", value=str(material.id)),
        )

    if back_value is not None:
        builder.button(text="Назад", callback_data=AppNav(screen=back_screen, value=back_value))
    else:
        builder.button(text="Назад", callback_data=AppNav(screen=back_screen))
    builder.button(text="В меню", callback_data=AppNav(screen="home"))
    builder.adjust(1)
    return builder.as_markup()


def build_material_detail_keyboard(material_id: int, is_favorite: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Убрать из избранного" if is_favorite else "В избранное",
        callback_data=AppNav(screen="toggle_favorite", value=str(material_id)),
    )
    builder.button(
        text="Удалить",
        callback_data=AppNav(screen="delete_material", value=str(material_id)),
    )
    builder.button(
        text="Редактировать в web",
        url=_build_web_cabinet_url(material_id=material_id),
    )
    builder.button(text="Назад в меню", callback_data=AppNav(screen="home"))
    builder.adjust(1)
    return builder.as_markup()


def build_add_category_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Без категории", callback_data=AppNav(screen="pick_category", value="none"))
    for category in categories:
        builder.button(
            text=category["name"],
            callback_data=AppNav(screen="pick_category", value=str(category["id"])),
        )
    builder.button(text="Новая категория", callback_data=AppNav(screen="new_category_in_flow"))
    builder.adjust(1)
    return builder.as_markup()


def _build_web_cabinet_url(material_id: int | None = None) -> str:
    query: dict[str, str] = {}
    if material_id is not None:
        query["material_id"] = str(material_id)
    if settings.web_cabinet_token:
        query["token"] = settings.web_cabinet_token

    if not query:
        return settings.mini_app_url

    separator = "&" if "?" in settings.mini_app_url else "?"
    return f"{settings.mini_app_url}{separator}{urlencode(query)}"
