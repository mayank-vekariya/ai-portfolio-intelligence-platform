from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv
from telegram import Update

from portfolio_bot.bot import PortfolioTelegramBot
from portfolio_bot.config import ConfigurationError, Settings
from portfolio_bot.database import Database
from portfolio_bot.market_data import build_market_provider
from portfolio_bot.services import PortfolioService


def main() -> None:
    load_dotenv()
    try:
        settings = Settings.from_env(require_token=True)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    database = Database(settings.database_path)
    database.initialize()
    provider = build_market_provider(
        settings.market_data_provider, cache_seconds=settings.market_cache_seconds
    )
    service = PortfolioService(database, provider)
    bot = PortfolioTelegramBot(settings, database, service)
    application = bot.build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
