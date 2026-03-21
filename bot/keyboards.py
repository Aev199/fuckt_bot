from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


ALL_TOPICS_VALUE = "all"


class TopicCallbackFactory(CallbackData, prefix="topic"):
    topic: str


class SessionActionCallbackFactory(CallbackData, prefix="session"):
    action: str
    value: str | None = None
    card_id: int | None = None


class ReminderCallbackFactory(CallbackData, prefix="reminder"):
    action: str
    value: str | None = None


def build_topics_keyboard(topics: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Все темы",
        callback_data=TopicCallbackFactory(topic=ALL_TOPICS_VALUE),
    )

    for topic in topics:
        builder.button(
            text=_prettify_topic(topic),
            callback_data=TopicCallbackFactory(topic=topic),
        )

    builder.adjust(1)
    return builder.as_markup()


def build_show_answer_keyboard(card_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Показать ответ",
        callback_data=SessionActionCallbackFactory(action="show_answer", card_id=card_id),
    )
    return builder.as_markup()


def build_rate_answer_keyboard(card_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✓ Знал",
        callback_data=SessionActionCallbackFactory(action="rate", value="knew", card_id=card_id),
    )
    builder.button(
        text="~ Сомневался",
        callback_data=SessionActionCallbackFactory(action="rate", value="unsure", card_id=card_id),
    )
    builder.button(
        text="✗ Не знал",
        callback_data=SessionActionCallbackFactory(action="rate", value="didnt", card_id=card_id),
    )
    builder.adjust(1)
    return builder.as_markup()


def build_session_summary_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Еще 5 вопросов",
        callback_data=SessionActionCallbackFactory(action="continue"),
    )
    builder.button(
        text="На сегодня хватит",
        callback_data=SessionActionCallbackFactory(action="stop"),
    )
    builder.adjust(1)
    return builder.as_markup()


def build_start_session_keyboard(topic: str | None = None, review_only: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Начать повторение" if review_only else "Начать сессию",
        callback_data=SessionActionCallbackFactory(
            action="start_review" if review_only else "start",
            value=topic or ALL_TOPICS_VALUE,
        ),
    )
    return builder.as_markup()


def build_reminder_time_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Утро (09:00 UTC)",
        callback_data=ReminderCallbackFactory(action="set_hour", value="9"),
    )
    builder.button(
        text="День (13:00 UTC)",
        callback_data=ReminderCallbackFactory(action="set_hour", value="13"),
    )
    builder.button(
        text="Вечер (18:00 UTC)",
        callback_data=ReminderCallbackFactory(action="set_hour", value="18"),
    )
    builder.button(
        text="Отключить напоминания",
        callback_data=ReminderCallbackFactory(action="disable"),
    )
    builder.adjust(1)
    return builder.as_markup()


def _prettify_topic(topic: str) -> str:
    return topic.replace("_", " ").strip().title()
