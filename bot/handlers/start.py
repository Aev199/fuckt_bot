from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import ALL_TOPICS_VALUE, SessionActionCallbackFactory, TopicCallbackFactory, build_topics_keyboard
from bot.states import SessionStates
from db.crud import get_topics
from db.models import User


logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(Command("start"))
async def cmd_start(
    message: Message,
    state: FSMContext,
    db_session: AsyncSession,
) -> None:
    await _show_topic_selection(
        message=message,
        state=state,
        db_session=db_session,
        greeting=(
            "Привет! Это тренажер по карточкам для геотехники.\n\n"
            "Выбери тему, и я начну короткую сессию на 5 вопросов."
        ),
    )


@router.message(Command("session"))
async def cmd_session(
    message: Message,
    state: FSMContext,
    db_session: AsyncSession,
) -> None:
    await _show_topic_selection(
        message=message,
        state=state,
        db_session=db_session,
        greeting="Выбери тему для новой сессии.",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Команды бота:\n"
        "/start — приветствие и выбор темы\n"
        "/session — начать сессию из 5 вопросов\n"
        "/stats — личная статистика\n"
        "/remind — настроить напоминания\n"
        "/help — показать эту справку"
    )


@router.callback_query(TopicCallbackFactory.filter())
async def process_topic_selection(
    callback: CallbackQuery,
    callback_data: TopicCallbackFactory,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    selected_topic = callback_data.topic

    await state.set_state(SessionStates.choosing_topic)
    await state.update_data(
        topic=selected_topic,
        review_only=False,
        session_count=0,
        knew_count=0,
        unsure_count=0,
        didnt_count=0,
        retry_queue=[],
        shown_card_ids=[],
    )

    await callback.answer("Тема выбрана")
    await _send_next_card(callback=callback, state=state, db_session=db_session, user=user)


@router.callback_query(SessionActionCallbackFactory.filter(F.action == "start"))
async def start_session_from_button(
    callback: CallbackQuery,
    callback_data: SessionActionCallbackFactory,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    selected_topic = callback_data.value or ALL_TOPICS_VALUE

    await state.set_state(SessionStates.choosing_topic)
    await state.update_data(
        topic=selected_topic,
        review_only=False,
        session_count=0,
        knew_count=0,
        unsure_count=0,
        didnt_count=0,
        retry_queue=[],
        shown_card_ids=[],
    )

    await callback.answer()
    await _send_next_card(callback=callback, state=state, db_session=db_session, user=user)


@router.callback_query(SessionActionCallbackFactory.filter(F.action == "start_review"))
async def start_review_from_button(
    callback: CallbackQuery,
    callback_data: SessionActionCallbackFactory,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    selected_topic = callback_data.value or ALL_TOPICS_VALUE

    await state.set_state(SessionStates.choosing_topic)
    await state.update_data(
        topic=selected_topic,
        review_only=True,
        session_count=0,
        knew_count=0,
        unsure_count=0,
        didnt_count=0,
        retry_queue=[],
        shown_card_ids=[],
    )

    await callback.answer()
    await _send_next_card(callback=callback, state=state, db_session=db_session, user=user)


async def _show_topic_selection(
    message: Message,
    state: FSMContext,
    db_session: AsyncSession,
    greeting: str,
) -> None:
    topics = await get_topics(db_session)
    if not topics:
        await state.clear()
        await message.answer(
            "Пока нет доступных карточек. Сначала загрузи cards.json в базу, затем попробуй снова."
        )
        return

    await state.set_state(SessionStates.choosing_topic)
    await state.update_data(
        topic=None,
        review_only=False,
        session_count=0,
        knew_count=0,
        unsure_count=0,
        didnt_count=0,
        retry_queue=[],
        shown_card_ids=[],
    )
    await message.answer(
        greeting,
        reply_markup=build_topics_keyboard(topics),
    )


async def _send_next_card(
    callback: CallbackQuery,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    try:
        from bot.handlers.session import send_next_card
    except ImportError:
        logger.exception("Session handler is not ready yet.")
        await callback.message.answer(
            "Основной сценарий сессии будет подключен на следующем шаге."
        )
        return

    await send_next_card(
        message=callback.message,
        state=state,
        db_session=db_session,
        user=user,
    )
