from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from config import settings
from db import crud
from db.models import Card, User, UserCard


async def _create_user(session, telegram_id: int = 1) -> User:
    user = User(telegram_id=telegram_id, username=f"user{telegram_id}")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_card(session, source_id: int, topic: str, question: str) -> Card:
    card = Card(
        source_id=source_id,
        card_type="recall",
        topic=topic,
        difficulty=1,
        question=question,
        answer=f"answer-{source_id}",
        active=True,
    )
    session.add(card)
    await session.commit()
    await session.refresh(card)
    return card


@pytest.mark.asyncio
async def test_get_next_card_priority_due_then_new_then_fallback(session_factory) -> None:
    async with session_factory() as session:
        user = await _create_user(session, telegram_id=10)
        due_card = await _create_card(session, 1, "soil", "due")
        new_card = await _create_card(session, 2, "soil", "new")
        fallback_card = await _create_card(session, 3, "soil", "fallback")

        due_progress = UserCard(
            user_id=user.id,
            card_id=due_card.id,
            result=crud.RESULT_UNSURE,
            shown_at=datetime.now(timezone.utc),
            next_review_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        fallback_progress = UserCard(
            user_id=user.id,
            card_id=fallback_card.id,
            result=crud.RESULT_KNEW,
            shown_at=datetime.now(timezone.utc),
            next_review_at=datetime.now(timezone.utc) + timedelta(days=5),
        )
        session.add_all([due_progress, fallback_progress])
        await session.commit()

        selected = await crud.get_next_card(session=session, user_id=user.id, topic="soil")
        assert selected is not None
        assert selected.id == due_card.id

        due_progress.next_review_at = datetime.now(timezone.utc) + timedelta(days=2)
        await session.commit()

        selected = await crud.get_next_card(session=session, user_id=user.id, topic="soil")
        assert selected is not None
        assert selected.id == new_card.id

        session.add(
            UserCard(
                user_id=user.id,
                card_id=new_card.id,
                result=crud.RESULT_UNSURE,
                shown_at=datetime.now(timezone.utc),
                next_review_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        await session.commit()

        selected = await crud.get_next_card(session=session, user_id=user.id, topic="soil")
        assert selected is not None
        assert selected.id == fallback_card.id


@pytest.mark.asyncio
async def test_save_result_uses_expected_review_intervals(session_factory) -> None:
    async with session_factory() as session:
        user = await _create_user(session, telegram_id=20)
        card = await _create_card(session, 20, "soil", "intervals")

        saved = await crud.save_result(session=session, user_id=user.id, card_id=card.id, result=crud.RESULT_KNEW)
        assert saved.next_review_at is not None
        knew_delta = saved.next_review_at - saved.shown_at
        assert settings.review_interval_knew_days <= knew_delta.days <= settings.review_interval_knew_days + 1

        saved = await crud.save_result(session=session, user_id=user.id, card_id=card.id, result=crud.RESULT_UNSURE)
        unsure_delta = saved.next_review_at - saved.shown_at
        assert settings.review_interval_unsure_days <= unsure_delta.days <= settings.review_interval_unsure_days + 1

        saved = await crud.save_result(session=session, user_id=user.id, card_id=card.id, result=crud.RESULT_DIDNT)
        didnt_delta = saved.next_review_at - saved.shown_at
        assert settings.review_interval_didnt_days <= didnt_delta.days <= settings.review_interval_didnt_days + 1


@pytest.mark.asyncio
async def test_due_only_mode_returns_only_due_cards(session_factory) -> None:
    async with session_factory() as session:
        user = await _create_user(session, telegram_id=30)
        due_card = await _create_card(session, 31, "soil", "due-only")
        await _create_card(session, 32, "soil", "new-only")

        progress = UserCard(
            user_id=user.id,
            card_id=due_card.id,
            result=crud.RESULT_UNSURE,
            shown_at=datetime.now(timezone.utc),
            next_review_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        session.add(progress)
        await session.commit()

        selected = await crud.get_next_card(session=session, user_id=user.id, due_only=True)
        assert selected is not None
        assert selected.id == due_card.id

        progress.next_review_at = datetime.now(timezone.utc) + timedelta(days=1)
        await session.commit()

        selected = await crud.get_next_card(session=session, user_id=user.id, due_only=True)
        assert selected is None


@pytest.mark.asyncio
async def test_get_user_stats_returns_aggregated_topic_data(session_factory) -> None:
    async with session_factory() as session:
        user = await _create_user(session, telegram_id=40)
        due_card = await _create_card(session, 41, "topic_a", "topic a due")
        seen_card = await _create_card(session, 42, "topic_a", "topic a seen")
        await _create_card(session, 43, "topic_b", "topic b unseen")
        inactive_card = await _create_card(session, 44, "topic_c", "topic c inactive")
        inactive_card.active = False

        session.add_all(
            [
                UserCard(
                    user_id=user.id,
                    card_id=due_card.id,
                    result=crud.RESULT_UNSURE,
                    shown_at=datetime.now(timezone.utc),
                    next_review_at=datetime.now(timezone.utc) - timedelta(hours=1),
                ),
                UserCard(
                    user_id=user.id,
                    card_id=seen_card.id,
                    result=crud.RESULT_KNEW,
                    shown_at=datetime.now(timezone.utc),
                    next_review_at=datetime.now(timezone.utc) + timedelta(days=7),
                ),
            ]
        )
        await session.commit()

        stats = await crud.get_user_stats(session=session, user_id=user.id)
        assert stats["total_seen"] == 2
        assert stats["knew"] == 1
        assert stats["unsure"] == 1
        assert stats["didnt"] == 0
        assert stats["due_now"] == 1
        assert stats["unseen_total"] == 1
        assert stats["topics_started"] == 1
        assert stats["topics_total"] == 2
        assert stats["topics"] == [
            {"topic": "topic_a", "viewed": 2, "due": 1, "unseen": 0},
            {"topic": "topic_b", "viewed": 0, "due": 0, "unseen": 1},
        ]
