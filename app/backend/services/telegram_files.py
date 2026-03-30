from __future__ import annotations

import httpx

from config import settings


async def download_telegram_file(file_path: str) -> bytes:
    file_url = f"https://api.telegram.org/file/bot{settings.bot_token}/{file_path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(file_url)
        response.raise_for_status()
        return response.content
