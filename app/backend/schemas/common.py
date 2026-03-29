from __future__ import annotations

from pydantic import BaseModel


class TelegramAuthRequest(BaseModel):
    init_data: str


class MessageResponse(BaseModel):
    message: str
