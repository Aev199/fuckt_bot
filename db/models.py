from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    notify_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    user_cards: Mapped[list["UserCard"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("notify_hour IS NULL OR notify_hour BETWEEN 0 AND 23", name="ck_users_notify_hour_range"),
    )


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_type: Mapped[str] = mapped_column(String(20), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subtopic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    options: Mapped[list[str] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    answer_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    user_cards: Mapped[list["UserCard"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("card_type IN ('recall', 'quiz')", name="ck_cards_card_type"),
        CheckConstraint("difficulty BETWEEN 1 AND 3", name="ck_cards_difficulty_range"),
        CheckConstraint(
            "(card_type = 'quiz' AND options IS NOT NULL AND answer_index IS NOT NULL) "
            "OR (card_type = 'recall' AND options IS NULL AND answer_index IS NULL)",
            name="ck_cards_quiz_fields",
        ),
    )


class UserCard(Base):
    __tablename__ = "user_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    shown_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    user: Mapped["User"] = relationship(back_populates="user_cards")
    card: Mapped["Card"] = relationship(back_populates="user_cards")

    __table_args__ = (
        UniqueConstraint("user_id", "card_id", name="uq_user_cards_user_card"),
        CheckConstraint("result IN ('knew', 'unsure', 'didnt')", name="ck_user_cards_result"),
    )
