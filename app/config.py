from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = Field(..., alias="BOT_TOKEN")
    public_channel_id: int = Field(..., alias="PUBLIC_CHANNEL_ID")
    admin_ids: str = Field(..., alias="ADMIN_IDS")
    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    timezone: str = Field(default="Europe/Minsk", alias="TIMEZONE")
    reminder_time: str = Field(default="12:00", alias="REMINDER_TIME")
    bump_interval_hours: int = Field(default=24, alias="BUMP_INTERVAL_HOURS")
    admin_basic_user: str = Field(..., alias="ADMIN_BASIC_USER")
    admin_basic_pass: str = Field(..., alias="ADMIN_BASIC_PASS")

    @property
    def admin_id_set(self) -> set[int]:
        return {int(item.strip()) for item in self.admin_ids.split(",") if item.strip()}


settings = Settings()
