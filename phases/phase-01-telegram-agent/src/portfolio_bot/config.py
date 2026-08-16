from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigurationError(ValueError):
    """Raised when runtime configuration is invalid."""


def parse_allowed_user_ids(raw: str | None) -> frozenset[int] | None:
    if raw is None or not raw.strip():
        return None
    try:
        values = frozenset(int(value.strip()) for value in raw.split(",") if value.strip())
    except ValueError as exc:
        raise ConfigurationError("ALLOWED_TELEGRAM_USER_IDS must contain numeric IDs") from exc
    if any(value <= 0 for value in values):
        raise ConfigurationError("Telegram user IDs must be positive")
    return values or None


def parse_clock(value: str, timezone_name: str) -> time:
    try:
        hour_text, minute_text = value.split(":", maxsplit=1)
        hour = int(hour_text)
        minute = int(minute_text)
        timezone = ZoneInfo(timezone_name)
        return time(hour=hour, minute=minute, tzinfo=timezone)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ConfigurationError(
            "Time must be HH:MM and timezone must be an IANA name such as America/Los_Angeles"
        ) from exc


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    database_path: Path
    market_data_provider: str
    market_cache_seconds: int
    default_timezone: str
    default_daily_brief_time: str
    allowed_user_ids: frozenset[int] | None
    log_level: str

    @classmethod
    def from_env(cls, require_token: bool = True) -> Settings:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if require_token and not token:
            raise ConfigurationError(
                "TELEGRAM_BOT_TOKEN is missing. Copy .env.example to .env "
                "and add a BotFather token."
            )

        database_path = Path(os.getenv("DATABASE_PATH", "data/portfolio_bot.sqlite3"))
        provider = os.getenv("MARKET_DATA_PROVIDER", "yahoo").strip().lower()
        if provider not in {"yahoo", "mock"}:
            raise ConfigurationError("MARKET_DATA_PROVIDER must be 'yahoo' or 'mock'")

        try:
            cache_seconds = int(os.getenv("MARKET_CACHE_SECONDS", "300"))
        except ValueError as exc:
            raise ConfigurationError("MARKET_CACHE_SECONDS must be an integer") from exc
        if cache_seconds < 0:
            raise ConfigurationError("MARKET_CACHE_SECONDS cannot be negative")

        timezone_name = os.getenv("DEFAULT_TIMEZONE", "America/Los_Angeles").strip()
        brief_time = os.getenv("DEFAULT_DAILY_BRIEF_TIME", "07:30").strip()
        parse_clock(brief_time, timezone_name)

        return cls(
            telegram_bot_token=token,
            database_path=database_path,
            market_data_provider=provider,
            market_cache_seconds=cache_seconds,
            default_timezone=timezone_name,
            default_daily_brief_time=brief_time,
            allowed_user_ids=parse_allowed_user_ids(os.getenv("ALLOWED_TELEGRAM_USER_IDS")),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        )
