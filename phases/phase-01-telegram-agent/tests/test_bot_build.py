from __future__ import annotations

from portfolio_bot.bot import PortfolioTelegramBot
from portfolio_bot.config import Settings
from portfolio_bot.database import Database
from portfolio_bot.market_data import MockMarketDataProvider
from portfolio_bot.services import PortfolioService


def test_telegram_application_builds_without_network_access(tmp_path) -> None:
    database = Database(tmp_path / "bot.sqlite3")
    database.initialize()
    settings = Settings(
        telegram_bot_token="123456789:" + ("A" * 35),
        database_path=tmp_path / "bot.sqlite3",
        market_data_provider="mock",
        market_cache_seconds=300,
        default_timezone="America/Los_Angeles",
        default_daily_brief_time="07:30",
        allowed_user_ids=frozenset({123}),
        log_level="INFO",
    )
    service = PortfolioService(database, MockMarketDataProvider())

    application = PortfolioTelegramBot(settings, database, service).build_application()

    command_handlers = application.handlers[0]
    assert len(command_handlers) >= 10
    assert application.job_queue is not None
