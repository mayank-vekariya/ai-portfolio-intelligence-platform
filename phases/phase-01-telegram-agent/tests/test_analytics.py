from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from portfolio_bot.analytics import analyze_security, build_portfolio_snapshot, build_risk_flags
from portfolio_bot.database import Holding
from portfolio_bot.market_data import DailyBar, MarketSnapshot


class StaticProvider:
    def __init__(self, values: dict[str, MarketSnapshot]) -> None:
        self.values = values

    async def get_snapshot(self, ticker: str) -> MarketSnapshot:
        return self.values[ticker]


def market(symbol: str, current: str, previous: str) -> MarketSnapshot:
    start = date(2026, 1, 1)
    bars = tuple(
        DailyBar(start + timedelta(days=index), Decimal("100") + Decimal(index))
        for index in range(60)
    )
    return MarketSnapshot(
        symbol=symbol,
        current_price=Decimal(current),
        previous_close=Decimal(previous),
        currency="USD",
        as_of=datetime(2026, 8, 14, tzinfo=UTC),
        history=bars,
        provider="test",
        prototype_only=True,
    )


def test_portfolio_calculation_and_concentration_flag() -> None:
    provider = StaticProvider(
        {"AAA": market("AAA", "120", "100"), "BBB": market("BBB", "50", "50")}
    )
    holdings = [
        Holding("AAA", Decimal("10"), Decimal("80")),
        Holding("BBB", Decimal("2"), Decimal("40")),
    ]
    snapshot = asyncio.run(build_portfolio_snapshot(holdings, Decimal("200"), provider))

    assert snapshot.invested_value == Decimal("1300")
    assert snapshot.total_value == Decimal("1500")
    assert snapshot.total_gain_loss == Decimal("420")
    assert snapshot.day_change == Decimal("200")
    assert snapshot.holdings[0].portfolio_weight_pct == Decimal("80.0")
    assert any(flag.title == "AAA concentration" for flag in build_risk_flags(snapshot))


def test_security_analysis_has_reproducible_metrics() -> None:
    analysis = analyze_security(market("AAA", "160", "159"))

    assert analysis.observations == 60
    assert analysis.moving_average_20d == Decimal("149.5")
    assert analysis.moving_average_50d == Decimal("134.5")
    assert analysis.max_drawdown_pct == Decimal("0")
    assert analysis.rsi_14d == Decimal("100")
