from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(..., alias="BOT_TOKEN")
    database_url: str = Field(..., alias="DATABASE_URL")
    admin_id: int = Field(..., alias="ADMIN_ID")

    bot_parse_mode: str = Field(default="HTML", alias="BOT_PARSE_MODE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    session_cards_limit: int = Field(default=5, alias="SESSION_CARDS_LIMIT")
    review_interval_knew_days: int = Field(default=7, alias="REVIEW_INTERVAL_KNEW_DAYS")
    review_interval_unsure_days: int = Field(default=1, alias="REVIEW_INTERVAL_UNSURE_DAYS")
    review_interval_didnt_days: int = Field(default=1, alias="REVIEW_INTERVAL_DIDNT_DAYS")
    scheduler_timezone: str = Field(default="UTC", alias="SCHEDULER_TIMEZONE")
    cards_json_path: str = Field(default="data/cards.json", alias="CARDS_JSON_PATH")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
