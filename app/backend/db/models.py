from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.backend.db.database import Base


class User(Base):
    __tablename__ = "kb_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    categories: Mapped[list["Category"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    materials: Mapped[list["Material"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tags: Mapped[list["Tag"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "kb_categories"
    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_kb_categories_user_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("kb_users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("kb_categories.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="categories")
    parent: Mapped["Category | None"] = relationship(remote_side="Category.id", back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent")
    materials: Mapped[list["Material"]] = relationship(back_populates="category")


class Material(Base):
    __tablename__ = "kb_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("kb_users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("kb_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="materials")
    category: Mapped[Category | None] = relationship(back_populates="materials")
    material_tags: Mapped[list["MaterialTag"]] = relationship(back_populates="material", cascade="all, delete-orphan")


class Tag(Base):
    __tablename__ = "kb_tags"
    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_kb_tags_user_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("kb_users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped[User] = relationship(back_populates="tags")
    material_tags: Mapped[list["MaterialTag"]] = relationship(back_populates="tag", cascade="all, delete-orphan")


class MaterialTag(Base):
    __tablename__ = "kb_material_tags"
    __table_args__ = (
        UniqueConstraint("material_id", "tag_id", name="uq_kb_material_tags_material_tag"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("kb_materials.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("kb_tags.id", ondelete="CASCADE"), nullable=False, index=True)

    material: Mapped[Material] = relationship(back_populates="material_tags")
    tag: Mapped[Tag] = relationship(back_populates="material_tags")
