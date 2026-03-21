from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import ReminderCallbackFactory, build_reminder_time_keyboard
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
        f"Сейчас напоминания включены на {user.notify_hour:02d}:00 UTC."
        if user.notifications_enabled and user.notify_hour is not None
        else "Сейчас напоминания отключены."
    )

    await state.set_state(NotificationStates.choosing_time)
    await message.answer(
        "Настройка напоминаний.\n\n"
        f"{current_status}\n"
        "Выбери удобное время в UTC или отключи напоминания.",
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

    await crud.set_user_notifications(
        session=db_session,
        user_id=user.id,
        enabled=True,
        notify_hour=notify_hour,
    )

    await state.clear()
    await callback.answer("Напоминания включены")

    if callback.message is not None:
        await callback.message.answer(
            f"Готово. Я буду присылать напоминание каждый день в {notify_hour:02d}:00 UTC."
        )


@router.callback_query(ReminderCallbackFactory.filter(F.action == "disable"))
async def disable_reminders(
    callback: CallbackQuery,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
) -> None:
    await crud.set_user_notifications(
        session=db_session,
        user_id=user.id,
        enabled=False,
        notify_hour=None,
    )

    await state.clear()
    await callback.answer("Напоминания отключены")

    if callback.message is not None:
        await callback.message.answer("Напоминания отключены. Включить их снова можно командой /remind.")
