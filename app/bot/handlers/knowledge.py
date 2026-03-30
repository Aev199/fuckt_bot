from __future__ import annotations

from urllib.parse import urlencode

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.db import crud
from app.backend.db.models import User
from app.backend.schemas.category import CategoryCreate
from app.backend.schemas.material import MaterialCreate
from app.bot.keyboards import (
    AppNav,
    build_add_category_keyboard,
    build_back_home_keyboard,
    build_categories_keyboard,
    build_home_keyboard,
    build_material_detail_keyboard,
    build_materials_keyboard,
)
from app.bot.states import AddMaterialStates, AttachmentStates, CategoryStates, SearchStates
from config import settings


router = Router(name="knowledge-bot")


@router.message(Command("start"))
@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _send_home(message)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Команды:\n"
        "/start или /menu — главное меню\n"
        "/add — добавить материал\n"
        "/search — поиск материалов\n"
        "/web — открыть web-кабинет\n"
        "/help — помощь"
    )


@router.message(Command("web"))
async def cmd_web(message: Message) -> None:
    await message.answer(
        "Web-кабинет для спокойного редактирования:\n"
        f"{_build_web_message_url()}\n\n"
        "Если открываешь его как обычный сайт, используй ссылку с токеном из `.env`."
    )


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext) -> None:
    await _start_add_flow(message=message, state=state)


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchStates.waiting_query)
    await message.answer(
        "Отправь поисковый запрос одним сообщением.\n"
        "Например: `сваи`, `суглинок`, `основание фундамента`.",
        reply_markup=build_back_home_keyboard(),
    )


@router.callback_query(AppNav.filter(F.screen == "home"))
async def show_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await _edit_or_answer(callback, _home_text(), build_home_keyboard())


@router.callback_query(AppNav.filter(F.screen == "add"))
async def callback_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.message:
        await _start_add_flow(message=callback.message, state=state)


@router.callback_query(AppNav.filter(F.screen == "search"))
async def callback_search(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(SearchStates.waiting_query)
    if callback.message:
        await callback.message.answer(
            "Отправь поисковый запрос одним сообщением.\n"
            "Я ищу по заголовку, тексту, заметкам и источнику.",
            reply_markup=build_back_home_keyboard(),
        )


@router.callback_query(AppNav.filter(F.screen == "categories"))
async def show_categories(
    callback: CallbackQuery,
    db_session: AsyncSession,
    user: User,
) -> None:
    await callback.answer()
    categories = await crud.list_categories(session=db_session, user_id=user.id)
    await _edit_or_answer(callback, _categories_text(categories), build_categories_keyboard(categories))


@router.callback_query(AppNav.filter(F.screen == "category"))
async def show_category_materials(
    callback: CallbackQuery,
    callback_data: AppNav,
    db_session: AsyncSession,
    user: User,
) -> None:
    await callback.answer()
    category_id = int(callback_data.value or "0")
    materials, total = await crud.list_materials(
        session=db_session,
        user_id=user.id,
        category_id=category_id,
        limit=20,
    )
    await _edit_or_answer(
        callback,
        _materials_list_text(f"Материалы в категории ({total})", materials),
        build_materials_keyboard(materials, back_screen="categories"),
    )


@router.callback_query(AppNav.filter(F.screen == "recent"))
async def show_recent(
    callback: CallbackQuery,
    db_session: AsyncSession,
    user: User,
) -> None:
    await callback.answer()
    materials, total = await crud.list_materials(session=db_session, user_id=user.id, limit=20)
    await _edit_or_answer(
        callback,
        _materials_list_text(f"Последние материалы ({total})", materials),
        build_materials_keyboard(materials, back_screen="home"),
    )


@router.callback_query(AppNav.filter(F.screen == "favorites"))
async def show_favorites(
    callback: CallbackQuery,
    db_session: AsyncSession,
    user: User,
) -> None:
    await callback.answer()
    materials, total = await crud.list_materials(session=db_session, user_id=user.id, favorite=True, limit=20)
    await _edit_or_answer(
        callback,
        _materials_list_text(f"Избранное ({total})", materials),
        build_materials_keyboard(materials, back_screen="home"),
    )


@router.callback_query(AppNav.filter(F.screen == "material"))
async def show_material(
    callback: CallbackQuery,
    callback_data: AppNav,
    db_session: AsyncSession,
    user: User,
) -> None:
    await callback.answer()
    material_id = int(callback_data.value or "0")
    try:
        material = await crud.get_material(session=db_session, user_id=user.id, material_id=material_id)
    except ValueError:
        await _edit_or_answer(callback, "Материал не найден.", build_back_home_keyboard())
        return

    await _edit_or_answer(
        callback,
        _material_text(crud.serialize_material(material)),
        _material_keyboard(material),
    )


@router.callback_query(AppNav.filter(F.screen == "toggle_favorite"))
async def toggle_favorite(
    callback: CallbackQuery,
    callback_data: AppNav,
    db_session: AsyncSession,
    user: User,
) -> None:
    material_id = int(callback_data.value or "0")
    material = await crud.toggle_favorite(session=db_session, user_id=user.id, material_id=material_id)
    await callback.answer("Обновил избранное")
    await _edit_or_answer(callback, _material_text(crud.serialize_material(material)), _material_keyboard(material))


@router.callback_query(AppNav.filter(F.screen == "attach_photo"))
async def start_attach_photo(
    callback: CallbackQuery,
    callback_data: AppNav,
    state: FSMContext,
) -> None:
    material_id = int(callback_data.value or "0")
    await state.set_state(AttachmentStates.waiting_photo)
    await state.update_data(material_id=material_id)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "Отправь фотографию одним сообщением.\n"
            "Подпись к фото сохранится как подпись вложения.\n"
            "Если передумал, нажми /menu."
        )


@router.callback_query(AppNav.filter(F.screen == "show_photos"))
async def show_photos(
    callback: CallbackQuery,
    callback_data: AppNav,
    db_session: AsyncSession,
    user: User,
) -> None:
    material_id = int(callback_data.value or "0")
    try:
        material = await crud.get_material(session=db_session, user_id=user.id, material_id=material_id)
    except ValueError:
        await callback.answer("Материал не найден", show_alert=True)
        return

    if not material.attachments:
        await callback.answer("У этого материала пока нет фото", show_alert=True)
        return

    await callback.answer()
    total = len(material.attachments)
    for index, attachment in enumerate(material.attachments, start=1):
        if not attachment.telegram_file_id or callback.message is None:
            continue

        caption_parts = [f"{material.title}\nФото {index} из {total}"]
        if attachment.caption:
            caption_parts.extend(["", attachment.caption])
        await callback.message.answer_photo(
            photo=attachment.telegram_file_id,
            caption="\n".join(caption_parts),
        )


@router.callback_query(AppNav.filter(F.screen == "delete_material"))
async def delete_material(
    callback: CallbackQuery,
    callback_data: AppNav,
    db_session: AsyncSession,
    user: User,
) -> None:
    material_id = int(callback_data.value or "0")
    await crud.delete_material(session=db_session, user_id=user.id, material_id=material_id)
    await callback.answer("Материал удалён")
    await _edit_or_answer(
        callback,
        _home_text() + "\n\nМатериал удалён.",
        build_home_keyboard(),
    )


@router.callback_query(AppNav.filter(F.screen == "new_category"))
async def start_new_category(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(CategoryStates.creating_name)
    await state.update_data(return_to="categories")
    if callback.message:
        await callback.message.answer("Отправь название новой категории.")


@router.callback_query(AppNav.filter(F.screen == "new_category_in_flow"))
async def start_new_category_in_flow(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(CategoryStates.creating_name)
    await state.update_data(return_to="add_category")
    if callback.message:
        await callback.message.answer("Отправь название новой категории, и я сразу подставлю её в материал.")


@router.message(CategoryStates.creating_name)
async def create_category_from_message(
    message: Message,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    category_name = (message.text or "").strip()
    if not category_name:
        await message.answer("Название не должно быть пустым. Попробуй ещё раз.")
        return

    category = await crud.create_category(
        session=db_session,
        user_id=user.id,
        payload=CategoryCreate(name=category_name),
    )
    state_data = await state.get_data()
    return_to = state_data.get("return_to")

    if return_to == "add_category":
        await state.update_data(category_id=category.id)
        await state.set_state(AddMaterialStates.tags)
        await message.answer(
            f"Категория `{category.name}` создана.\n"
            "Теперь отправь теги через запятую или `-`, если тегов нет."
        )
        return

    await state.clear()
    categories = await crud.list_categories(session=db_session, user_id=user.id)
    await message.answer(
        f"Категория `{category.name}` создана.",
        reply_markup=build_categories_keyboard(categories),
    )


@router.message(SearchStates.waiting_query)
async def process_search_query(
    message: Message,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer("Запрос пустой. Отправь текст для поиска.")
        return

    materials, total = await crud.list_materials(session=db_session, user_id=user.id, q=query, limit=20)
    await state.clear()
    await message.answer(
        _materials_list_text(f"Результаты поиска по запросу: {query} ({total})", materials),
        reply_markup=build_materials_keyboard(materials, back_screen="home"),
    )


@router.callback_query(StateFilter(AddMaterialStates.category), AppNav.filter(F.screen == "pick_category"))
async def pick_category_for_add(
    callback: CallbackQuery,
    callback_data: AppNav,
    state: FSMContext,
) -> None:
    selected = callback_data.value
    category_id = None if selected == "none" else int(selected or "0")
    await state.update_data(category_id=category_id)
    await state.set_state(AddMaterialStates.tags)
    await callback.answer("Категория выбрана")
    if callback.message:
        await callback.message.answer(
            "Отправь теги через запятую.\n"
            "Если тегов нет, отправь `-`."
        )


@router.message(AddMaterialStates.title)
async def add_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Заголовок не должен быть пустым. Попробуй ещё раз.")
        return

    await state.update_data(title=title)
    await state.set_state(AddMaterialStates.content)
    await message.answer("Теперь отправь основной текст материала.")


@router.message(AddMaterialStates.content)
async def add_content(message: Message, state: FSMContext) -> None:
    content = (message.text or "").strip()
    if not content:
        await message.answer("Текст не должен быть пустым. Попробуй ещё раз.")
        return

    await state.update_data(content=content)
    await state.set_state(AddMaterialStates.source_url)
    await message.answer("Отправь ссылку на источник или `-`, если её нет.")


@router.message(AddMaterialStates.source_url)
async def add_source_url(message: Message, state: FSMContext) -> None:
    await state.update_data(source_url=_normalize_optional_text(message.text))
    await state.set_state(AddMaterialStates.source_name)
    await message.answer("Теперь отправь короткое имя источника или `-`, если не нужно.")


@router.message(AddMaterialStates.source_name)
async def add_source_name(message: Message, state: FSMContext) -> None:
    await state.update_data(source_name=_normalize_optional_text(message.text))
    await state.set_state(AddMaterialStates.notes)
    await message.answer("Отправь личные заметки или `-`, если пока без заметок.")


@router.message(AddMaterialStates.notes)
async def add_notes(message: Message, state: FSMContext, db_session: AsyncSession, user: User) -> None:
    await state.update_data(notes=_normalize_optional_text(message.text))
    await state.set_state(AddMaterialStates.category)
    categories = await crud.list_categories(session=db_session, user_id=user.id)
    await message.answer(
        "Выбери категорию для материала.",
        reply_markup=build_add_category_keyboard(categories),
    )


@router.message(AddMaterialStates.tags)
async def add_tags(
    message: Message,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    state_data = await state.get_data()
    payload = MaterialCreate(
        title=state_data["title"],
        content=state_data["content"],
        source_url=state_data.get("source_url"),
        source_name=state_data.get("source_name"),
        notes=state_data.get("notes"),
        category_id=state_data.get("category_id"),
        tags=_parse_tags(message.text),
    )
    material = await crud.create_material(session=db_session, user_id=user.id, payload=payload)
    await state.clear()
    await message.answer(
        "Материал сохранён.\n\n" + _material_text(crud.serialize_material(material)),
        reply_markup=_material_keyboard(material),
    )


@router.message(AttachmentStates.waiting_photo, F.photo)
async def save_attachment_photo(
    message: Message,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    state_data = await state.get_data()
    material_id = state_data.get("material_id")
    if material_id is None:
        await state.clear()
        await message.answer("Не удалось понять, к какому материалу прикрепить фото. Попробуй снова из карточки материала.")
        return

    photo = message.photo[-1]
    telegram_file = await bot.get_file(photo.file_id)
    await crud.add_material_attachment(
        session=db_session,
        user_id=user.id,
        material_id=int(material_id),
        telegram_file_id=photo.file_id,
        file_path=telegram_file.file_path,
        file_name=f"telegram_photo_{photo.file_unique_id}.jpg",
        mime_type="image/jpeg",
        caption=(message.caption or "").strip() or None,
    )
    material = await crud.get_material(session=db_session, user_id=user.id, material_id=int(material_id))
    await state.clear()
    await message.answer(
        "Фото добавлено.\n\n" + _material_text(crud.serialize_material(material)),
        reply_markup=_material_keyboard(material),
    )


@router.message(AttachmentStates.waiting_photo)
async def attachment_waiting_non_photo(message: Message) -> None:
    await message.answer("Сейчас я жду фотографию. Отправь фото одним сообщением или нажми /menu для выхода.")


async def _start_add_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddMaterialStates.title)
    await state.update_data(category_id=None)
    await message.answer(
        "Добавляем новый материал.\n\n"
        "Шаг 1 из 7: отправь заголовок."
    )


async def _send_home(message: Message) -> None:
    await message.answer(_home_text(), reply_markup=build_home_keyboard())


async def _edit_or_answer(source: CallbackQuery, text: str, reply_markup) -> None:
    if source.message is None:
        return

    try:
        await source.message.edit_text(text=text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await source.message.answer(text=text, reply_markup=reply_markup)


def _home_text() -> str:
    return (
        "База знаний по геотехнике\n\n"
        "Что можно делать:\n"
        "• быстро сохранять полезные материалы\n"
        "• прикреплять фото к материалам\n"
        "• искать по ключевым словам\n"
        "• ходить по категориям\n"
        "• открывать избранное и последние материалы\n"
        "• при необходимости редактировать через web"
    )


def _categories_text(categories: list[dict]) -> str:
    if not categories:
        return "Категорий пока нет.\n\nСоздай первую кнопкой ниже."

    lines = ["Категории:"]
    for category in categories:
        lines.append(f"• {category['name']} — {category['materials_count']} материалов")
    return "\n".join(lines)


def _materials_list_text(title: str, materials: list) -> str:
    if not materials:
        return f"{title}\n\nНичего не найдено."

    lines = [title, ""]
    for material in materials[:10]:
        attachment_suffix = f" [{len(material.attachments)} фото]" if getattr(material, "attachments", None) else ""
        lines.append(f"• {material.title}{attachment_suffix}")
    return "\n".join(lines)


def _material_text(material) -> str:
    parts = [
        material.title,
        "",
        f"Категория: {material.category_name or 'Без категории'}",
    ]

    if material.source_name:
        parts.append(f"Источник: {material.source_name}")
    if material.source_url:
        parts.append(f"Ссылка: {material.source_url}")

    parts.extend(["", material.content])

    if material.notes:
        parts.extend(["", f"Заметки: {material.notes}"])

    if material.tags:
        parts.extend(["", f"Теги: {', '.join(material.tags)}"])

    if material.attachments:
        parts.extend(["", f"Вложений: {len(material.attachments)}"])

    if material.is_favorite:
        parts.extend(["", "★ В избранном"])

    return "\n".join(parts)


def _normalize_optional_text(text: str | None) -> str | None:
    value = (text or "").strip()
    if not value or value == "-":
        return None
    return value


def _parse_tags(text: str | None) -> list[str]:
    value = _normalize_optional_text(text)
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _build_web_message_url() -> str:
    query: dict[str, str] = {}
    if settings.web_cabinet_token:
        query["token"] = settings.web_cabinet_token

    if not query:
        return settings.mini_app_url

    separator = "&" if "?" in settings.mini_app_url else "?"
    return f"{settings.mini_app_url}{separator}{urlencode(query)}"


def _material_keyboard(material) -> object:
    return build_material_detail_keyboard(
        material_id=material.id,
        is_favorite=material.is_favorite,
        attachments_count=len(material.attachments),
    )
