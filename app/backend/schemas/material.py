from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime


class MaterialListResponse(BaseModel):
    items: list[MaterialRead]
    total: int
