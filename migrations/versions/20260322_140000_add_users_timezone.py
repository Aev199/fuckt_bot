"""add users timezone

Revision ID: 20260322_140000
Revises: 20260322_120000
Create Date: 2026-03-22 14:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260322_140000"
down_revision = "20260322_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("timezone", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "timezone")
