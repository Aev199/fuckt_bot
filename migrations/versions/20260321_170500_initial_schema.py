"""initial schema

Revision ID: 20260321_170500
Revises:
Create Date: 2026-03-21 17:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260321_170500"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("card_type", sa.String(length=20), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("subtopic", sa.String(length=255), nullable=True),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("hint", sa.Text(), nullable=True),
        sa.Column("options", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("answer_index", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.CheckConstraint("card_type IN ('recall', 'quiz')", name="ck_cards_card_type"),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 3", name="ck_cards_difficulty_range"),
        sa.CheckConstraint(
            "(card_type = 'quiz' AND options IS NOT NULL AND answer_index IS NOT NULL) "
            "OR (card_type = 'recall' AND options IS NULL AND answer_index IS NULL)",
            name="ck_cards_quiz_fields",
        ),
        sa.UniqueConstraint("question"),
    )
    op.create_index("ix_cards_difficulty", "cards", ["difficulty"], unique=False)
    op.create_index("ix_cards_topic", "cards", ["topic"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notify_hour", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.CheckConstraint("notify_hour IS NULL OR notify_hour BETWEEN 0 AND 23", name="ck_users_notify_hour_range"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "user_cards",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("result IN ('knew', 'unsure', 'didnt')", name="ck_user_cards_result"),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "card_id", name="uq_user_cards_user_card"),
    )
    op.create_index("ix_user_cards_card_id", "user_cards", ["card_id"], unique=False)
    op.create_index("ix_user_cards_next_review_at", "user_cards", ["next_review_at"], unique=False)
    op.create_index("ix_user_cards_shown_at", "user_cards", ["shown_at"], unique=False)
    op.create_index("ix_user_cards_user_id", "user_cards", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_cards_user_id", table_name="user_cards")
    op.drop_index("ix_user_cards_shown_at", table_name="user_cards")
    op.drop_index("ix_user_cards_next_review_at", table_name="user_cards")
    op.drop_index("ix_user_cards_card_id", table_name="user_cards")
    op.drop_table("user_cards")

    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_cards_topic", table_name="cards")
    op.drop_index("ix_cards_difficulty", table_name="cards")
    op.drop_table("cards")
