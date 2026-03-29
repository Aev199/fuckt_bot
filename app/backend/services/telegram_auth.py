from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

from fastapi import HTTPException, status

from config import settings


@dataclass(slots=True)
class TelegramWebAppUser:
    telegram_id: int
    username: str | None


def validate_init_data(init_data: str) -> TelegramWebAppUser:
    if not init_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Telegram init data")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Telegram hash")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram signature")

    auth_date = parsed.get("auth_date")
    if auth_date:
        auth_datetime = datetime.fromtimestamp(int(auth_date), tz=timezone.utc)
        if datetime.now(timezone.utc) - auth_datetime > timedelta(days=1):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram auth data expired")

    user_payload = parsed.get("user")
    if not user_payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Telegram user payload")

    user_data = json.loads(user_payload)
    return TelegramWebAppUser(
        telegram_id=int(user_data["id"]),
        username=user_data.get("username"),
    )
