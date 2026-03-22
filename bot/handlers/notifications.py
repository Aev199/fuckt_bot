from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import (
    ReminderCallbackFactory,
    TIMEZONE_CHOICES,
    build_reminder_opt_in_keyboard,
    build_reminder_time_keyboard,
    build_timezone_keyboard,
)
from bot.states import NotificationStates
from db import crud
from db.models import User


router = Router(name="notifications")


@router.message(Command("remind"))
async def cmd_remind(
    message: Message,
    state: FSMContext,
    user: User,
) -> None:
    current_status = (
        f"Сейчас напоминания включены на {user.notify_hour:02d}:00 ({_timezone_label(user.timezone)})."
        if user.notifications_enabled and user.notify_hour is not None and user.timezone
        else "Сейчас напоминания отключены."
    )

    await _ask_timezone(message=message, state=state, intro=f"Настройка напоминаний.\n\n{current_status}")


@router.callback_query(ReminderCallbackFactory.filter(F.action == "opt_in"))
async def opt_in_reminders(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.message is not None:
        await _ask_timezone(
            message=callback.message,
            state=state,
            intro="Отлично. Сначала выбери свой часовой пояс.",
        )


@router.callback_query(ReminderCallbackFactory.filter(F.action == "later"))
async def remind_later(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Хорошо, настроим позже")
    if callback.message is not None:
        await callback.message.answer("Без проблем. Напоминания можно включить позже через /remind.")


@router.callback_query(ReminderCallbackFactory.filter(F.action == "set_timezone"))
async def set_timezone(
    callback: CallbackQuery,
    callback_data: ReminderCallbackFactory,
    state: FSMContext,
) -> None:
    timezone_name = callback_data.value
    if timezone_name is None:
        await callback.answer("Не удалось определить часовой пояс", show_alert=True)
        return

    await state.update_data(selected_timezone=timezone_name)
    await state.set_state(NotificationStates.choosing_time)
    await callback.answer("Часовой пояс сохранён")

    if callback.message is not None:
        await callback.message.answer(
            f"Часовой пояс: {_timezone_label(timezone_name)}.\nТеперь выбери удобное время напоминания.",
            reply_markup=build_reminder_time_keyboard(),
        )


@router.callback_query(ReminderCallbackFactory.filter(F.action == "set_hour"))
async def set_reminder_hour(
    callback: CallbackQuery,
    callback_data: ReminderCallbackFactory,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    if callback_data.value is None:
        await callback.answer("Не удалось определить время", show_alert=True)
        return

    notify_hour = int(callback_data.value)
    if notify_hour < 0 or notify_hour > 23:
        await callback.answer("Некорректный час напоминания", show_alert=True)
        return

    state_data = await state.get_data()
    timezone_name = state_data.get("selected_timezone") or user.timezone
    if not timezone_name:
        await callback.answer("Сначала выбери часовой пояс", show_alert=True)
        return

    await crud.configure_user_notifications(
        session=db_session,
        user_id=user.id,
        timezone_name=timezone_name,
        notify_hour=notify_hour,
    )

    await state.clear()
    await callback.answer("Напоминания включены")

    if callback.message is not None:
        await callback.message.answer(
            f"Готово. Я буду присылать напоминание каждый день в {notify_hour:02d}:00 по часовому поясу {_timezone_label(timezone_name)}."
        )


@router.callback_query(ReminderCallbackFactory.filter(F.action == "disable"))
async def disable_reminders(
    callback: CallbackQuery,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    await crud.disable_user_notifications(session=db_session, user_id=user.id)

    await state.clear()
    await callback.answer("Напоминания отключены")

    if callback.message is not None:
        await callback.message.answer("Напоминания отключены. Включить их снова можно командой /remind.")


async def _ask_timezone(message: Message, state: FSMContext, intro: str) -> None:
    await state.set_state(NotificationStates.choosing_timezone)
    await state.update_data(selected_timezone=None)
    await message.answer(
        f"{intro}\n\nВыбери свой часовой пояс.",
        reply_markup=build_timezone_keyboard(),
    )


def _timezone_label(timezone_name: str | None) -> str:
    if timezone_name is None:
        return "не выбран"

    for label, value in TIMEZONE_CHOICES:
        if value == timezone_name:
            return label

    return timezone_name
