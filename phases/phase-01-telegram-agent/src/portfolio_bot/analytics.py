from __future__ import annotations

import asyncio
import math
import statistics
from dataclasses import dataclass
from decimal import Decimal

from portfolio_bot.database import Holding
from portfolio_bot.market_data import MarketDataProvider, MarketSnapshot

ZERO = Decimal("0")
HUNDRED = Decimal("100")


@dataclass(frozen=True)
class HoldingSnapshot:
    ticker: str
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal
    previous_close: Decimal
    market_value: Decimal
    cost_basis: Decimal
    gain_loss: Decimal
    gain_loss_pct: Decimal
    day_change: Decimal
    day_change_pct: Decimal
    portfolio_weight_pct: Decimal
    market: MarketSnapshot


@dataclass(frozen=True)
class PortfolioSnapshot:
    holdings: tuple[HoldingSnapshot, ...]
    cash: Decimal
    invested_value: Decimal
    total_value: Decimal
    cost_basis: Decimal
    total_gain_loss: Decimal
    total_gain_loss_pct: Decimal
    day_change: Decimal
    day_change_pct: Decimal
    unavailable_tickers: tuple[str, ...]


@dataclass(frozen=True)
class RiskFlag:
    severity: str
    title: str
    detail: str


@dataclass(frozen=True)
class SecurityAnalysis:
    ticker: str
    label: str
    current_price: Decimal
    day_change_pct: Decimal
    momentum_20d_pct: Decimal | None
    moving_average_20d: Decimal | None
    moving_average_50d: Decimal | None
    annualized_volatility_pct: Decimal | None
    max_drawdown_pct: Decimal | None
    rsi_14d: Decimal | None
    observations: int
    market: MarketSnapshot


def _safe_percent(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return ZERO
    return (numerator / denominator) * HUNDRED


async def build_portfolio_snapshot(
    holdings: list[Holding], cash: Decimal, provider: MarketDataProvider
) -> PortfolioSnapshot:
    results = await asyncio.gather(
        *(provider.get_snapshot(holding.ticker) for holding in holdings), return_exceptions=True
    )
    available: list[tuple[Holding, MarketSnapshot]] = []
    unavailable: list[str] = []
    for holding, result in zip(holdings, results, strict=True):
        if isinstance(result, BaseException):
            unavailable.append(holding.ticker)
        else:
            available.append((holding, result))

    invested_value = sum(
        (holding.quantity * market.current_price for holding, market in available), ZERO
    )
    total_value = invested_value + cash
    cost_basis = sum((holding.quantity * holding.average_cost for holding, _ in available), ZERO)
    total_gain_loss = invested_value - cost_basis
    previous_invested = sum(
        (holding.quantity * market.previous_close for holding, market in available), ZERO
    )
    day_change = invested_value - previous_invested

    snapshots: list[HoldingSnapshot] = []
    for holding, market in available:
        market_value = holding.quantity * market.current_price
        holding_cost_basis = holding.quantity * holding.average_cost
        gain_loss = market_value - holding_cost_basis
        snapshots.append(
            HoldingSnapshot(
                ticker=holding.ticker,
                quantity=holding.quantity,
                average_cost=holding.average_cost,
                current_price=market.current_price,
                previous_close=market.previous_close,
                market_value=market_value,
                cost_basis=holding_cost_basis,
                gain_loss=gain_loss,
                gain_loss_pct=_safe_percent(gain_loss, holding_cost_basis),
                day_change=holding.quantity * market.day_change,
                day_change_pct=market.day_change_pct,
                portfolio_weight_pct=_safe_percent(market_value, total_value),
                market=market,
            )
        )
    snapshots.sort(key=lambda item: item.market_value, reverse=True)

    return PortfolioSnapshot(
        holdings=tuple(snapshots),
        cash=cash,
        invested_value=invested_value,
        total_value=total_value,
        cost_basis=cost_basis,
        total_gain_loss=total_gain_loss,
        total_gain_loss_pct=_safe_percent(total_gain_loss, cost_basis),
        day_change=day_change,
        day_change_pct=_safe_percent(day_change, previous_invested + cash),
        unavailable_tickers=tuple(unavailable),
    )


def build_risk_flags(snapshot: PortfolioSnapshot) -> tuple[RiskFlag, ...]:
    flags: list[RiskFlag] = []
    if not snapshot.holdings:
        flags.append(
            RiskFlag(
                severity="INFO",
                title="No priced holdings",
                detail="Add a holding before the bot can evaluate portfolio-level risk.",
            )
        )
    for holding in snapshot.holdings:
        if holding.portfolio_weight_pct >= Decimal("30"):
            flags.append(
                RiskFlag(
                    severity="HIGH",
                    title=f"{holding.ticker} concentration",
                    detail=(
                        f"{holding.ticker} is {holding.portfolio_weight_pct:.1f}% of the tracked "
                        "portfolio. Compare that exposure with your own maximum-position rule."
                    ),
                )
            )
        elif holding.portfolio_weight_pct >= Decimal("20"):
            flags.append(
                RiskFlag(
                    severity="MEDIUM",
                    title=f"{holding.ticker} position size",
                    detail=(
                        f"{holding.ticker} is {holding.portfolio_weight_pct:.1f}% "
                        "of tracked value."
                    ),
                )
            )
        if abs(holding.day_change_pct) >= Decimal("5"):
            flags.append(
                RiskFlag(
                    severity="MEDIUM",
                    title=f"{holding.ticker} material move",
                    detail=f"The latest session move is {holding.day_change_pct:+.1f}%.",
                )
            )
        if holding.gain_loss_pct <= Decimal("-20"):
            flags.append(
                RiskFlag(
                    severity="MEDIUM",
                    title=f"{holding.ticker} thesis review",
                    detail=(
                        f"The tracked position is {holding.gain_loss_pct:.1f}% below average cost. "
                        "Recheck the original thesis instead of reacting to price alone."
                    ),
                )
            )
    if snapshot.unavailable_tickers:
        flags.append(
            RiskFlag(
                severity="HIGH",
                title="Incomplete data",
                detail="No current data for: " + ", ".join(snapshot.unavailable_tickers),
            )
        )
    if not flags:
        flags.append(
            RiskFlag(
                severity="INFO",
                title="No threshold alert",
                detail=(
                    "No configured MVP threshold was crossed. "
                    "This is not a statement of safety."
                ),
            )
        )
    order = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
    return tuple(sorted(flags, key=lambda flag: order[flag.severity]))


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, ZERO) / Decimal(len(values))


def analyze_security(market: MarketSnapshot) -> SecurityAnalysis:
    closes = [bar.close for bar in market.history if bar.close > 0]
    observations = len(closes)
    ma20 = _mean(closes[-20:]) if observations >= 20 else None
    ma50 = _mean(closes[-50:]) if observations >= 50 else None
    momentum20 = (
        _safe_percent(closes[-1] - closes[-21], closes[-21]) if observations >= 21 else None
    )

    returns = [
        float((current / previous) - Decimal("1"))
        for previous, current in zip(closes, closes[1:], strict=False)
        if previous != 0
    ]
    volatility = None
    if len(returns) >= 20:
        volatility = Decimal(str(statistics.stdev(returns) * math.sqrt(252) * 100))

    max_drawdown = None
    if closes:
        peak = closes[0]
        worst = ZERO
        for close in closes:
            peak = max(peak, close)
            drawdown = _safe_percent(close - peak, peak)
            worst = min(worst, drawdown)
        max_drawdown = worst

    rsi = None
    if observations >= 15:
        deltas = [current - previous for previous, current in zip(closes, closes[1:], strict=False)]
        recent = deltas[-14:]
        average_gain = _mean([max(delta, ZERO) for delta in recent])
        average_loss = _mean([abs(min(delta, ZERO)) for delta in recent])
        if average_loss == 0:
            rsi = HUNDRED
        else:
            relative_strength = average_gain / average_loss
            rsi = HUNDRED - (HUNDRED / (Decimal("1") + relative_strength))

    label = "MIXED / NEEDS REVIEW"
    if volatility is not None and volatility >= Decimal("60"):
        label = "HIGH VOLATILITY"
    elif max_drawdown is not None and max_drawdown <= Decimal("-25"):
        label = "HIGH DRAWDOWN"
    elif ma20 is not None and ma50 is not None:
        if market.current_price > ma20 > ma50:
            label = "CONSTRUCTIVE TREND"
        elif market.current_price < ma20 < ma50:
            label = "WEAKENING TREND"
        if rsi is not None and rsi >= Decimal("70") and market.current_price > ma20:
            label = "EXTENDED / AVOID CHASING"

    return SecurityAnalysis(
        ticker=market.symbol,
        label=label,
        current_price=market.current_price,
        day_change_pct=market.day_change_pct,
        momentum_20d_pct=momentum20,
        moving_average_20d=ma20,
        moving_average_50d=ma50,
        annualized_volatility_pct=volatility,
        max_drawdown_pct=max_drawdown,
        rsi_14d=rsi,
        observations=observations,
        market=market,
    )
