from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MaterialAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_file_id: str | None
    file_name: str | None
    mime_type: str | None
    caption: str | None
    sort_order: int
    created_at: datetime


class MaterialBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source_url: str | None = None
    source_name: str | None = None
    notes: str | None = None
    category_id: int | None = None
    tags: list[str] = []


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    source_url: str | None = None
    source_name: str | None = None
    notes: str | None = None
    category_id: int | None = None
    tags: list[str] | None = None
    is_favorite: bool | None = None


class MaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    source_url: str | None
    source_name: str | None
    notes: str | None
    is_favorite: bool
    category_id: int | None
    category_name: str | None = None
    top_category_id: int | None = None
    top_category_name: str | None = None
    subcategory_id: int | None = None
    subcategory_name: str | None = None
    tags: list[str] = []
    attachments: list[MaterialAttachmentRead] = []
    created_at: datetime
    updated_at: datetime


class MaterialListResponse(BaseModel):
    items: list[MaterialRead]
    total: int
