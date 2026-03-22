from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from db.models import User


router = Router(name="stats")


@router.message(Command("stats"))
async def cmd_stats(
    message: Message,
    db_session: AsyncSession,
    user: User,
) -> None:
    stats = await crud.get_user_stats(session=db_session, user_id=user.id)
    topic_lines = [
        (
            f"{_humanize_topic(topic_stats['topic'])}: "
            f"изучено {topic_stats['viewed']}, "
            f"на повторении {topic_stats['due']}, "
            f"новых {topic_stats['unseen']}"
        )
        for topic_stats in stats["topics"]
    ]
    topics_block = "\n".join(topic_lines) if topic_lines else "Пока нет активных тем."

    await message.answer(
        "Твоя статистика:\n\n"
        f"Просмотрено карточек: {stats['total_seen']}\n"
        f"Знал: {stats['knew']}\n"
        f"Сомневался: {stats['unsure']}\n"
        f"Не знал: {stats['didnt']}\n"
        f"На повторение сейчас: {stats['due_now']}\n"
        f"Новых карточек впереди: {stats['unseen_total']}\n"
        f"Тем начато: {stats['topics_started']} из {stats['topics_total']}\n\n"
        "По темам:\n"
        f"{topics_block}"
    )


def _humanize_topic(value: str) -> str:
    return value.replace("_", " ").strip().title()
