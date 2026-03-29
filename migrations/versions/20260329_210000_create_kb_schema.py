"""create knowledge base schema

Revision ID: 20260329_210000
Revises: 20260322_140000
Create Date: 2026-03-29 21:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_210000"
down_revision = "20260322_140000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "kb_users" not in existing_tables:
        op.create_table(
            "kb_users",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("telegram_id", sa.BigInteger(), nullable=False),
            sa.Column("username", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("telegram_id"),
        )
        op.create_index("ix_kb_users_telegram_id", "kb_users", ["telegram_id"], unique=True)

    if "kb_categories" not in existing_tables:
        op.create_table(
            "kb_categories",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["parent_id"], ["kb_categories.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["kb_users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "slug", name="uq_kb_categories_user_slug"),
        )
        op.create_index("ix_kb_categories_user_id", "kb_categories", ["user_id"], unique=False)

    if "kb_materials" not in existing_tables:
        op.create_table(
            "kb_materials",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("category_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source_url", sa.String(length=2048), nullable=True),
            sa.Column("source_name", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["category_id"], ["kb_categories.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["kb_users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_kb_materials_user_id", "kb_materials", ["user_id"], unique=False)
        op.create_index("ix_kb_materials_category_id", "kb_materials", ["category_id"], unique=False)
        op.create_index("ix_kb_materials_title", "kb_materials", ["title"], unique=False)

    if "kb_tags" not in existing_tables:
        op.create_table(
            "kb_tags",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["kb_users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "slug", name="uq_kb_tags_user_slug"),
        )
        op.create_index("ix_kb_tags_user_id", "kb_tags", ["user_id"], unique=False)

    if "kb_material_tags" not in existing_tables:
        op.create_table(
            "kb_material_tags",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("material_id", sa.Integer(), nullable=False),
            sa.Column("tag_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["material_id"], ["kb_materials.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tag_id"], ["kb_tags.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("material_id", "tag_id", name="uq_kb_material_tags_material_tag"),
        )
        op.create_index("ix_kb_material_tags_material_id", "kb_material_tags", ["material_id"], unique=False)
        op.create_index("ix_kb_material_tags_tag_id", "kb_material_tags", ["tag_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "kb_material_tags" in existing_tables:
        op.drop_index("ix_kb_material_tags_tag_id", table_name="kb_material_tags")
        op.drop_index("ix_kb_material_tags_material_id", table_name="kb_material_tags")
        op.drop_table("kb_material_tags")

    if "kb_tags" in existing_tables:
        op.drop_index("ix_kb_tags_user_id", table_name="kb_tags")
        op.drop_table("kb_tags")

    if "kb_materials" in existing_tables:
        op.drop_index("ix_kb_materials_title", table_name="kb_materials")
        op.drop_index("ix_kb_materials_category_id", table_name="kb_materials")
        op.drop_index("ix_kb_materials_user_id", table_name="kb_materials")
        op.drop_table("kb_materials")

    if "kb_categories" in existing_tables:
        op.drop_index("ix_kb_categories_user_id", table_name="kb_categories")
        op.drop_table("kb_categories")

    if "kb_users" in existing_tables:
        op.drop_index("ix_kb_users_telegram_id", table_name="kb_users")
        op.drop_table("kb_users")
