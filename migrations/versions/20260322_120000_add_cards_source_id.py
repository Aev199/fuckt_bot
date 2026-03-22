"""add cards source_id

Revision ID: 20260322_120000
Revises: 20260321_170500
Create Date: 2026-03-22 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260322_120000"
down_revision = "20260321_170500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cards", sa.Column("source_id", sa.Integer(), nullable=True))
    op.execute("UPDATE cards SET source_id = id WHERE source_id IS NULL")
    op.create_index("ix_cards_source_id", "cards", ["source_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_cards_source_id", table_name="cards")
    op.drop_column("cards", "source_id")
