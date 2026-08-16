from __future__ import annotations

import asyncio
from decimal import Decimal

from portfolio_bot.database import Database
from portfolio_bot.market_data import MockMarketDataProvider
from portfolio_bot.services import PortfolioService, truncate_message


def test_daily_brief_and_security_review(tmp_path) -> None:
    database = Database(tmp_path / "service.sqlite3")
    database.initialize()
    database.register_user(7, 7, "Seven", "America/Los_Angeles", "07:30")
    database.set_cash(7, Decimal("1000"))
    database.set_holding(7, "AAPL", Decimal("10"), Decimal("150"))
    service = PortfolioService(database, MockMarketDataProvider())

    brief = asyncio.run(service.daily_brief_text(7))
    review = asyncio.run(service.security_text("AAPL"))

    assert "DAILY PORTFOLIO BRIEF" in brief
    assert "MARKET PULSE" in brief
    assert "No order was or can be placed" in brief
    assert "AAPL REVIEW" in review
    assert "not a buy or sell recommendation" in review


def test_truncate_message_stays_under_telegram_limit() -> None:
    result = truncate_message("x" * 5000)
    assert len(result) <= 4000
    assert result.endswith("[Message truncated]")
