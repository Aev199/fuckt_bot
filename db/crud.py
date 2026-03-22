from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import Card, User, UserCard


RESULT_KNEW = "knew"
RESULT_UNSURE = "unsure"
RESULT_DIDNT = "didnt"
ALL_TOPICS_VALUE = "all"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_topic(topic: str | None) -> str | None:
    if topic is None:
        return None

    normalized_topic = topic.strip()
    if not normalized_topic or normalized_topic.lower() == ALL_TOPICS_VALUE:
        return None

    return normalized_topic


def _review_datetime(result: str, now: datetime) -> datetime:
    interval_days = {
        RESULT_KNEW: settings.review_interval_knew_days,
        RESULT_UNSURE: settings.review_interval_unsure_days,
        RESULT_DIDNT: settings.review_interval_didnt_days,
    }.get(result)

    if interval_days is None:
        raise ValueError(f"Unsupported result: {result}")

    return now + timedelta(days=interval_days)


def _card_filters(topic: str | None, exclude_card_ids: Sequence[int] | None) -> list:
    filters = [Card.active.is_(True)]

    normalized_topic = _normalize_topic(topic)
    if normalized_topic is not None:
        filters.append(Card.topic == normalized_topic)

    if exclude_card_ids:
        filters.append(Card.id.notin_(list(exclude_card_ids)))

    return filters


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    statement = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    statement = select(User).where(User.id == user_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, telegram_id: int, username: str | None = None) -> User:
    user = User(
        telegram_id=telegram_id,
        username=username,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None = None) -> User:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None:
        return await create_user(session=session, telegram_id=telegram_id, username=username)

    updated = False
    if user.username != username:
        user.username = username
        updated = True

    if not user.is_active:
        user.is_active = True
        updated = True

    if updated:
        await session.commit()
        await session.refresh(user)

    return user


async def get_topics(session: AsyncSession) -> list[str]:
    statement = (
        select(Card.topic)
        .where(Card.active.is_(True))
        .distinct()
        .order_by(Card.topic.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def count_seen_cards(session: AsyncSession, user_id: int) -> int:
    statement = select(func.count(UserCard.id)).where(UserCard.user_id == user_id)
    result = await session.execute(statement)
    return result.scalar_one()


async def get_card_by_id(session: AsyncSession, card_id: int) -> Card | None:
    statement = select(Card).where(Card.id == card_id, Card.active.is_(True))
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_next_card(
    session: AsyncSession,
    user_id: int,
    topic: str | None = None,
    exclude_card_ids: Sequence[int] | None = None,
    due_only: bool = False,
) -> Card | None:
    filters = _card_filters(topic=topic, exclude_card_ids=exclude_card_ids)
    now = _utc_now()

    due_statement = (
        select(Card)
        .join(UserCard, UserCard.card_id == Card.id)
        .where(
            *filters,
            UserCard.user_id == user_id,
            UserCard.next_review_at.is_not(None),
            UserCard.next_review_at <= now,
        )
        .order_by(UserCard.next_review_at.asc(), func.random())
        .limit(1)
    )
    due_result = await session.execute(due_statement)
    due_card = due_result.scalar_one_or_none()
    if due_card is not None:
        return due_card

    if due_only:
        return None

    new_statement = (
        select(Card)
        .outerjoin(
            UserCard,
            and_(
                UserCard.card_id == Card.id,
                UserCard.user_id == user_id,
            ),
        )
        .where(
            *filters,
            UserCard.id.is_(None),
        )
        .order_by(func.random())
        .limit(1)
    )
    new_result = await session.execute(new_statement)
    new_card = new_result.scalar_one_or_none()
    if new_card is not None:
        return new_card

    fallback_statement = (
        select(Card)
        .join(UserCard, UserCard.card_id == Card.id)
        .where(
            *filters,
            UserCard.user_id == user_id,
            UserCard.result == RESULT_KNEW,
        )
        .order_by(func.random())
        .limit(1)
    )
    fallback_result = await session.execute(fallback_statement)
    return fallback_result.scalar_one_or_none()


async def save_result(session: AsyncSession, user_id: int, card_id: int, result: str) -> UserCard:
    now = _utc_now()
    next_review_at = _review_datetime(result=result, now=now)

    statement = select(UserCard).where(
        UserCard.user_id == user_id,
        UserCard.card_id == card_id,
    )
    existing_result = await session.execute(statement)
    user_card = existing_result.scalar_one_or_none()

    if user_card is None:
        user_card = UserCard(
            user_id=user_id,
            card_id=card_id,
            result=result,
            shown_at=now,
            next_review_at=next_review_at,
        )
        session.add(user_card)
    else:
        user_card.result = result
        user_card.shown_at = now
        user_card.next_review_at = next_review_at

    await session.commit()
    await session.refresh(user_card)
    return user_card


async def get_user_stats(session: AsyncSession, user_id: int) -> dict[str, int]:
    now = _utc_now()

    total_seen = await count_seen_cards(session=session, user_id=user_id)

    knew_count = (
        await session.execute(
            select(func.count(UserCard.id)).where(
                UserCard.user_id == user_id,
                UserCard.result == RESULT_KNEW,
            )
        )
    ).scalar_one()

    unsure_count = (
        await session.execute(
            select(func.count(UserCard.id)).where(
                UserCard.user_id == user_id,
                UserCard.result == RESULT_UNSURE,
            )
        )
    ).scalar_one()

    didnt_count = (
        await session.execute(
            select(func.count(UserCard.id)).where(
                UserCard.user_id == user_id,
                UserCard.result == RESULT_DIDNT,
            )
        )
    ).scalar_one()

    due_count = (
        await session.execute(
            select(func.count(UserCard.id))
            .select_from(UserCard)
            .join(Card, Card.id == UserCard.card_id)
            .where(
                UserCard.user_id == user_id,
                UserCard.next_review_at.is_not(None),
                UserCard.next_review_at <= now,
                Card.active.is_(True),
            )
        )
    ).scalar_one()

    total_topics = (
        await session.execute(
            select(func.count(func.distinct(Card.topic))).where(Card.active.is_(True))
        )
    ).scalar_one()

    topics_started = (
        await session.execute(
            select(func.count(func.distinct(Card.topic)))
            .select_from(UserCard)
            .join(Card, Card.id == UserCard.card_id)
            .where(UserCard.user_id == user_id, Card.active.is_(True))
        )
    ).scalar_one()

    unseen_total = (
        await session.execute(
            select(func.count(Card.id))
            .select_from(Card)
            .outerjoin(
                UserCard,
                and_(
                    UserCard.card_id == Card.id,
                    UserCard.user_id == user_id,
                ),
            )
            .where(Card.active.is_(True), UserCard.id.is_(None))
        )
    ).scalar_one()

    topic_rows = (
        await session.execute(
            select(Card.topic)
            .where(Card.active.is_(True))
            .distinct()
            .order_by(Card.topic.asc())
        )
    ).scalars().all()

    topics: list[dict[str, int | str]] = []
    for topic in topic_rows:
        viewed_in_topic = (
            await session.execute(
                select(func.count(UserCard.id))
                .select_from(UserCard)
                .join(Card, Card.id == UserCard.card_id)
                .where(UserCard.user_id == user_id, Card.active.is_(True), Card.topic == topic)
            )
        ).scalar_one()

        due_in_topic = (
            await session.execute(
                select(func.count(UserCard.id))
                .select_from(UserCard)
                .join(Card, Card.id == UserCard.card_id)
                .where(
                    UserCard.user_id == user_id,
                    UserCard.next_review_at.is_not(None),
                    UserCard.next_review_at <= now,
                    Card.active.is_(True),
                    Card.topic == topic,
                )
            )
        ).scalar_one()

        unseen_in_topic = (
            await session.execute(
                select(func.count(Card.id))
                .select_from(Card)
                .outerjoin(
                    UserCard,
                    and_(
                        UserCard.card_id == Card.id,
                        UserCard.user_id == user_id,
                    ),
                )
                .where(Card.active.is_(True), Card.topic == topic, UserCard.id.is_(None))
            )
        ).scalar_one()

        topics.append(
            {
                "topic": topic,
                "viewed": viewed_in_topic,
                "due": due_in_topic,
                "unseen": unseen_in_topic,
            }
        )

    return {
        "total_seen": total_seen,
        "knew": knew_count,
        "unsure": unsure_count,
        "didnt": didnt_count,
        "due_now": due_count,
        "unseen_total": unseen_total,
        "topics_started": topics_started,
        "topics_total": total_topics,
        "topics": topics,
    }


async def configure_user_notifications(
    session: AsyncSession,
    user_id: int,
    timezone_name: str,
    notify_hour: int | None,
) -> User:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
    user.notifications_enabled = True
    user.timezone = timezone_name
    user.notify_hour = notify_hour

    await session.commit()
    await session.refresh(user)
    return user


async def disable_user_notifications(session: AsyncSession, user_id: int) -> User:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
    user.notifications_enabled = False
    user.notify_hour = None

    await session.commit()
    await session.refresh(user)
    return user


async def count_due_cards(session: AsyncSession, user_id: int, topic: str | None = None) -> int:
    now = _utc_now()
    filters = [UserCard.user_id == user_id, UserCard.next_review_at.is_not(None), UserCard.next_review_at <= now]

    normalized_topic = _normalize_topic(topic)
    statement = (
        select(func.count(UserCard.id))
        .select_from(UserCard)
        .join(Card, Card.id == UserCard.card_id)
        .where(*filters, Card.active.is_(True))
    )

    if normalized_topic is not None:
        statement = statement.where(Card.topic == normalized_topic)

    result = await session.execute(statement)
    return result.scalar_one()


async def get_users_with_notifications_enabled(session: AsyncSession) -> list[User]:
    statement = (
        select(User)
        .where(
            User.is_active.is_(True),
            User.notifications_enabled.is_(True),
        )
        .order_by(User.id.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_admin_stats(session: AsyncSession) -> dict[str, int]:
    now = _utc_now()

    total_users = (await session.execute(select(func.count(User.id)))).scalar_one()
    users_with_progress = (
        await session.execute(
            select(func.count(func.distinct(UserCard.user_id))).select_from(UserCard)
        )
    ).scalar_one()
    reminders_enabled = (
        await session.execute(
            select(func.count(User.id)).where(User.notifications_enabled.is_(True))
        )
    ).scalar_one()
    active_cards = (
        await session.execute(
            select(func.count(Card.id)).where(Card.active.is_(True))
        )
    ).scalar_one()
    active_topics = (
        await session.execute(
            select(func.count(func.distinct(Card.topic))).where(Card.active.is_(True))
        )
    ).scalar_one()
    due_reviews_total = (
        await session.execute(
            select(func.count(UserCard.id))
            .select_from(UserCard)
            .join(Card, Card.id == UserCard.card_id)
            .where(
                UserCard.next_review_at.is_not(None),
                UserCard.next_review_at <= now,
                Card.active.is_(True),
            )
        )
    ).scalar_one()

    return {
        "total_users": total_users,
        "users_with_progress": users_with_progress,
        "reminders_enabled": reminders_enabled,
        "active_cards": active_cards,
        "active_topics": active_topics,
        "due_reviews_total": due_reviews_total,
    }
