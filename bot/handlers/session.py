from __future__ import annotations

import html
import logging
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import (
    ALL_TOPICS_VALUE,
    SessionActionCallbackFactory,
    build_rate_answer_keyboard,
    build_session_summary_keyboard,
    build_show_answer_keyboard,
)
from bot.states import SessionStates
from config import settings
from db import crud
from db.models import Card, User


logger = logging.getLogger(__name__)

router = Router(name="session")

_CITE_PATTERN = re.compile(r"\[cite:\s*[^\]]+\]")
_INLINE_FORMULA_PATTERN = re.compile(r"\$(.+?)\$")


@router.callback_query(SessionActionCallbackFactory.filter(F.action == "show_answer"))
async def show_answer(
    callback: CallbackQuery,
    callback_data: SessionActionCallbackFactory,
    state: FSMContext,
    db_session: AsyncSession,
) -> None:
    state_data = await state.get_data()
    card_id = state_data.get("current_card_id")

    if card_id is None:
        await callback.answer("Сначала начни сессию", show_alert=True)
        return

    if callback_data.card_id != card_id:
        await callback.answer("Эта карточка уже неактуальна", show_alert=True)
        return

    card = await crud.get_card_by_id(db_session, card_id)
    if card is None:
        logger.warning("Card not found while showing answer: card_id=%s", card_id)
        await callback.answer("Карточка не найдена", show_alert=True)
        return

    await callback.answer()
    await _edit_or_send_answer(
        message=callback.message,
        text=_build_answer_text(card),
        reply_markup=build_rate_answer_keyboard(card.id),
    )
    await state.set_state(SessionStates.answer_shown)


@router.callback_query(SessionActionCallbackFactory.filter(F.action == "rate"))
async def rate_answer(
    callback: CallbackQuery,
    callback_data: SessionActionCallbackFactory,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    result = callback_data.value
    if result not in {crud.RESULT_KNEW, crud.RESULT_UNSURE, crud.RESULT_DIDNT}:
        await callback.answer("Неизвестная оценка", show_alert=True)
        return

    state_data = await state.get_data()
    card_id = state_data.get("current_card_id")
    if card_id is None:
        await callback.answer("Нет активной карточки", show_alert=True)
        return

    if callback_data.card_id != card_id:
        await callback.answer("Эта карточка уже неактуальна", show_alert=True)
        return

    await crud.save_result(
        session=db_session,
        user_id=user.id,
        card_id=card_id,
        result=result,
    )

    session_count = int(state_data.get("session_count", 0)) + 1
    knew_count = int(state_data.get("knew_count", 0))
    unsure_count = int(state_data.get("unsure_count", 0))
    didnt_count = int(state_data.get("didnt_count", 0))
    retry_queue = list(state_data.get("retry_queue", []))

    if result == crud.RESULT_KNEW:
        knew_count += 1
    elif result == crud.RESULT_UNSURE:
        unsure_count += 1
    else:
        didnt_count += 1
        retry_queue.append(card_id)

    await state.update_data(
        session_count=session_count,
        knew_count=knew_count,
        unsure_count=unsure_count,
        didnt_count=didnt_count,
        retry_queue=retry_queue,
        current_card_id=None,
    )

    await callback.answer()

    if session_count < settings.session_cards_limit:
        await send_next_card(
            message=callback.message,
            state=state,
            db_session=db_session,
            user=user,
        )
        return

    await show_session_summary(message=callback.message, state=state)


@router.callback_query(SessionActionCallbackFactory.filter(F.action == "continue"))
async def continue_session(
    callback: CallbackQuery,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    state_data = await state.get_data()
    topic = state_data.get("topic", ALL_TOPICS_VALUE)
    review_only = bool(state_data.get("review_only", False))

    await state.set_state(SessionStates.choosing_topic)
    await state.update_data(
        topic=topic,
        review_only=review_only,
        session_count=0,
        knew_count=0,
        unsure_count=0,
        didnt_count=0,
        retry_queue=[],
        shown_card_ids=[],
        current_card_id=None,
    )

    await callback.answer()
    await send_next_card(
        message=callback.message,
        state=state,
        db_session=db_session,
        user=user,
    )


@router.callback_query(SessionActionCallbackFactory.filter(F.action == "stop"))
async def stop_session(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer()

    if callback.message is not None:
        await callback.message.answer("Сессию завершили. Возвращайся, когда захочешь продолжить.")


async def send_next_card(
    message: Message | None,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    if message is None:
        logger.error("send_next_card called without a message object.")
        return

    state_data = await state.get_data()
    session_count = int(state_data.get("session_count", 0))
    topic = _normalize_topic(state_data.get("topic"))
    review_only = bool(state_data.get("review_only", False))
    shown_card_ids = list(state_data.get("shown_card_ids", []))
    retry_queue = list(state_data.get("retry_queue", []))
    remaining_slots = settings.session_cards_limit - session_count

    if remaining_slots <= 0:
        await show_session_summary(message=message, state=state)
        return

    card: Card | None = None
    if retry_queue and remaining_slots <= len(retry_queue):
        card = await _pop_retry_card(db_session=db_session, retry_queue=retry_queue)

    if card is None:
        card = await crud.get_next_card(
            session=db_session,
            user_id=user.id,
            topic=topic,
            exclude_card_ids=shown_card_ids,
            due_only=review_only,
        )

    if card is None and retry_queue:
        card = await _pop_retry_card(db_session=db_session, retry_queue=retry_queue)

    if card is None:
        await state.set_state(SessionStates.session_done)
        await state.update_data(
            retry_queue=retry_queue,
            current_card_id=None,
        )
        await message.answer("Все карточки пройдены.")
        return

    if card.id not in shown_card_ids:
        shown_card_ids.append(card.id)

    await state.set_state(SessionStates.in_session)
    await state.update_data(
        current_card_id=card.id,
        review_only=review_only,
        shown_card_ids=shown_card_ids,
        retry_queue=retry_queue,
    )

    await message.answer(
        _build_question_text(card),
        reply_markup=build_show_answer_keyboard(card.id),
    )


async def show_session_summary(message: Message | None, state: FSMContext) -> None:
    if message is None:
        logger.error("show_session_summary called without a message object.")
        return

    state_data = await state.get_data()
    knew_count = int(state_data.get("knew_count", 0))
    unsure_count = int(state_data.get("unsure_count", 0))
    didnt_count = int(state_data.get("didnt_count", 0))
    session_count = int(state_data.get("session_count", 0))

    await state.set_state(SessionStates.session_done)
    await state.update_data(current_card_id=None)

    await message.answer(
        "Сессия завершена.\n\n"
        f"Всего вопросов: {session_count}\n"
        f"Знал: {knew_count}\n"
        f"Сомневался: {unsure_count}\n"
        f"Не знал: {didnt_count}",
        reply_markup=build_session_summary_keyboard(),
    )


async def _edit_or_send_answer(
    message: Message | None,
    text: str,
    reply_markup,
) -> None:
    if message is None:
        logger.error("Cannot show answer: callback message is missing.")
        return

    try:
        await message.edit_text(text=text, reply_markup=reply_markup)
    except TelegramBadRequest:
        logger.warning("Failed to edit message, sending a new one instead.", exc_info=True)
        await message.answer(text=text, reply_markup=reply_markup)


async def _pop_retry_card(db_session: AsyncSession, retry_queue: list[int]) -> Card | None:
    while retry_queue:
        card_id = retry_queue.pop(0)
        card = await crud.get_card_by_id(db_session, card_id)
        if card is not None:
            return card

        logger.warning("Retry card not found or inactive: card_id=%s", card_id)

    return None


def _build_question_text(card: Card) -> str:
    topic_line = _format_card_meta(card)
    options_block = _format_options(card)

    text = f"{topic_line}\n\nВопрос:\n{_render_card_text(card.question)}"
    if options_block:
        text += f"\n\n{options_block}"

    return text


def _build_answer_text(card: Card) -> str:
    topic_line = _format_card_meta(card)
    options_block = _format_options(card)

    parts = [
        topic_line,
        "",
        "Вопрос:",
        _render_card_text(card.question),
    ]

    if options_block:
        parts.extend(["", options_block])

    parts.extend(["", "Ответ:", _render_card_text(card.answer)])

    if card.hint:
        parts.extend(["", f"Подсказка: {_render_card_text(card.hint)}"])

    return "\n".join(parts)


def _format_card_meta(card: Card) -> str:
    topic = html.escape(_humanize_label(card.topic))
    meta_parts = [f"Тема: {topic}", f"Сложность: {card.difficulty}"]

    if card.subtopic:
        meta_parts.insert(1, f"Подтема: {html.escape(_humanize_label(card.subtopic))}")

    return "\n".join(meta_parts)


def _format_options(card: Card) -> str:
    if not card.options:
        return ""

    options_lines = [f"{index + 1}. {_render_card_text(option)}" for index, option in enumerate(card.options)]
    return "Варианты:\n" + "\n".join(options_lines)


def _humanize_label(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _normalize_topic(topic: str | None) -> str | None:
    if topic is None or topic == ALL_TOPICS_VALUE:
        return None
    return topic


def _render_card_text(text: str) -> str:
    cleaned_text = _CITE_PATTERN.sub("", text).strip()
    if not cleaned_text:
        return ""

    rendered_parts: list[str] = []
    last_index = 0

    for match in _INLINE_FORMULA_PATTERN.finditer(cleaned_text):
        rendered_parts.append(html.escape(cleaned_text[last_index:match.start()]))
        rendered_parts.append(f"<code>{html.escape(_normalize_formula(match.group(1)))}</code>")
        last_index = match.end()

    rendered_parts.append(html.escape(cleaned_text[last_index:]))
    return "".join(rendered_parts).strip()


def _normalize_formula(formula: str) -> str:
    replacements = {
        r"\le": "<=",
        r"\ge": ">=",
        r"\cdot": "*",
        r"\rho": "rho",
        r"\alpha": "alpha",
        r"\beta": "beta",
        r"\gamma": "gamma",
        r"\Delta": "Delta",
    }

    normalized = formula.strip()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)

    normalized = normalized.replace("{", "").replace("}", "")
    normalized = normalized.replace("\\", "")
    return normalized
