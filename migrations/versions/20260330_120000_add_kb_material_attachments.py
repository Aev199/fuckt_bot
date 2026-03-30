"""add knowledge base material attachments

Revision ID: 20260330_120000
Revises: 20260329_210000
Create Date: 2026-03-30 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260330_120000"
down_revision = "20260329_210000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "kb_material_attachments" not in existing_tables:
        op.create_table(
            "kb_material_attachments",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("material_id", sa.Integer(), nullable=False),
            sa.Column("telegram_file_id", sa.String(length=255), nullable=True),
            sa.Column("file_path", sa.String(length=2048), nullable=True),
            sa.Column("file_name", sa.String(length=255), nullable=True),
            sa.Column("mime_type", sa.String(length=255), nullable=True),
            sa.Column("caption", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["material_id"], ["kb_materials.id"], ondelete="CASCADE"),
        )
        op.create_index(
            "ix_kb_material_attachments_material_id",
            "kb_material_attachments",
            ["material_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "kb_material_attachments" in existing_tables:
        op.drop_index("ix_kb_material_attachments_material_id", table_name="kb_material_attachments")
        op.drop_table("kb_material_attachments")
