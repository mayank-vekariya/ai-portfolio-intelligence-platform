from __future__ import annotations

import asyncio
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

from portfolio_bot.database import Database
from portfolio_bot.market_data import MockMarketDataProvider
from portfolio_bot.services import PortfolioService


async def run_demo() -> None:
    with tempfile.TemporaryDirectory(prefix="portfolio-bot-demo-") as directory:
        database = Database(Path(directory) / "demo.sqlite3")
        database.initialize()
        user_id = 1001
        database.register_user(
            user_id,
            chat_id=1001,
            display_name="Demo User",
            timezone="America/Los_Angeles",
            daily_brief_time="07:30",
        )
        database.set_cash(user_id, Decimal("2500"))
        database.set_holding(user_id, "AAPL", Decimal("12"), Decimal("175"))
        database.set_holding(user_id, "MSFT", Decimal("6"), Decimal("410"))
        database.set_holding(user_id, "NVDA", Decimal("8"), Decimal("160"))
        service = PortfolioService(database, MockMarketDataProvider())
        print(await service.daily_brief_text(user_id))
        print("\n" + "=" * 72 + "\n")
        print(await service.security_text("NVDA"))


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
