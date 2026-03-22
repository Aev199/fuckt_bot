from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from data.load_cards import sync_cards
from db.models import Card, User, UserCard


@pytest.mark.asyncio
async def test_sync_cards_inserts_updates_and_deactivates_removed_cards(session_factory) -> None:
    async with session_factory() as session:
        existing = Card(
            source_id=1,
            card_type="recall",
            topic="soil",
            difficulty=1,
            question="old question",
            answer="old answer",
            active=True,
        )
        removed = Card(
            source_id=2,
            card_type="recall",
            topic="soil",
            difficulty=1,
            question="removed question",
            answer="removed answer",
            active=True,
        )
        user = User(telegram_id=777, username="sync-user")
        session.add_all([existing, removed, user])
        await session.commit()
        await session.refresh(existing)
        await session.refresh(removed)
        await session.refresh(user)

        session.add(
            UserCard(
                user_id=user.id,
                card_id=removed.id,
                result="knew",
                shown_at=datetime.now(timezone.utc),
                next_review_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        summary = await sync_cards(
            session=session,
            prepared_cards=[
                {
                    "source_id": 1,
                    "card_type": "recall",
                    "topic": "soil",
                    "subtopic": None,
                    "difficulty": 2,
                    "question": "new question",
                    "answer": "new answer",
                    "hint": None,
                    "active": True,
                    "options": None,
                    "answer_index": None,
                },
                {
                    "source_id": 3,
                    "card_type": "recall",
                    "topic": "rock",
                    "subtopic": None,
                    "difficulty": 1,
                    "question": "brand new",
                    "answer": "brand new answer",
                    "hint": None,
                    "active": True,
                    "options": None,
                    "answer_index": None,
                },
            ],
        )

        assert summary == {"inserted": 1, "updated": 1, "unchanged": 0, "deactivated": 1}

        cards = list((await session.execute(select(Card).order_by(Card.source_id.asc()))).scalars().all())
        assert [(card.source_id, card.question, card.active) for card in cards] == [
            (1, "new question", True),
            (2, "removed question", False),
            (3, "brand new", True),
        ]

        user_card = (
            await session.execute(select(UserCard).where(UserCard.card_id == removed.id))
        ).scalar_one()
        assert user_card is not None
