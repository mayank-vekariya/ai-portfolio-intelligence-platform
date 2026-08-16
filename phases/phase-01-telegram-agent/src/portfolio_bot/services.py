from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from portfolio_bot.analytics import (
    PortfolioSnapshot,
    SecurityAnalysis,
    analyze_security,
    build_portfolio_snapshot,
    build_risk_flags,
)
from portfolio_bot.database import Database
from portfolio_bot.market_data import MarketDataError, MarketDataProvider


def money(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def percent(value: Decimal | None) -> str:
    return "n/a" if value is None else f"{value:+.1f}%"


def number(value: Decimal | None) -> str:
    return "n/a" if value is None else f"{value:,.2f}"


def truncate_message(value: str, limit: int = 4000) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 30].rstrip() + "\n\n[Message truncated]"


class PortfolioService:
    def __init__(self, database: Database, market_data: MarketDataProvider) -> None:
        self.database = database
        self.market_data = market_data

    async def snapshot(self, user_id: int) -> PortfolioSnapshot:
        return await build_portfolio_snapshot(
            self.database.list_holdings(user_id),
            self.database.get_cash(user_id),
            self.market_data,
        )

    async def portfolio_text(self, user_id: int) -> str:
        snapshot = await self.snapshot(user_id)
        if not snapshot.holdings and not snapshot.unavailable_tickers:
            return (
                "Your tracked portfolio is empty.\n\n"
                "Add a position with:\n/add AAPL 10 185.50\n"
                "Set tracked cash with:\n/cash 1000"
            )
        lines = [
            "📊 TRACKED PORTFOLIO",
            "",
            f"Total value: {money(snapshot.total_value)}",
            f"Invested: {money(snapshot.invested_value)}",
            f"Tracked cash: {money(snapshot.cash)}",
            f"Latest session: {money(snapshot.day_change)} ({percent(snapshot.day_change_pct)})",
            f"Since average cost: {money(snapshot.total_gain_loss)} "
            f"({percent(snapshot.total_gain_loss_pct)})",
            "",
            "HOLDINGS",
        ]
        for holding in snapshot.holdings:
            lines.extend(
                [
                    f"{holding.ticker} • {holding.portfolio_weight_pct:.1f}% of tracked value",
                    f"  {format(holding.quantity.normalize(), 'f')} shares @ "
                    f"{money(holding.current_price)}",
                    f"  Value {money(holding.market_value)} • P/L {money(holding.gain_loss)} "
                    f"({percent(holding.gain_loss_pct)})",
                ]
            )
        if snapshot.unavailable_tickers:
            lines.extend(["", "Data unavailable: " + ", ".join(snapshot.unavailable_tickers)])
        lines.extend(["", self._data_notice(snapshot)])
        return truncate_message("\n".join(lines))

    async def risk_text(self, user_id: int) -> str:
        snapshot = await self.snapshot(user_id)
        flags = build_risk_flags(snapshot)
        icons = {"HIGH": "🔴", "MEDIUM": "🟡", "INFO": "🔵"}
        lines = ["🛡️ PORTFOLIO REVIEW", ""]
        for flag in flags:
            lines.append(f"{icons[flag.severity]} {flag.title}")
            lines.append(flag.detail)
            lines.append("")
        lines.append("Thresholds are educational defaults, not personalized financial advice.")
        return truncate_message("\n".join(lines))

    async def security_text(self, ticker: str) -> str:
        try:
            market = await self.market_data.get_snapshot(ticker)
        except MarketDataError:
            return f"I could not load enough reliable data for {ticker}. Try again later."
        analysis = analyze_security(market)
        return truncate_message(self._format_security_analysis(analysis))

    async def watchlist_text(self, user_id: int) -> str:
        tickers = self.database.list_watchlist(user_id)
        if not tickers:
            return "Your watchlist is empty. Add one with /watch NVDA"
        results = await asyncio.gather(
            *(self.market_data.get_snapshot(ticker) for ticker in tickers), return_exceptions=True
        )
        lines = ["👀 WATCHLIST", ""]
        for ticker, result in zip(tickers, results, strict=True):
            if isinstance(result, BaseException):
                lines.append(f"{ticker}: data unavailable")
            else:
                lines.append(
                    f"{ticker}: {money(result.current_price)} ({percent(result.day_change_pct)})"
                )
        return "\n".join(lines)

    async def daily_brief_text(self, user_id: int) -> str:
        user = self.database.get_user(user_id)
        timezone = ZoneInfo(user.timezone) if user else ZoneInfo("UTC")
        now = datetime.now(tz=timezone)
        snapshot_task = self.snapshot(user_id)
        benchmark_tasks = [
            self.market_data.get_snapshot(symbol) for symbol in ("SPY", "QQQ", "IWM")
        ]
        snapshot, *benchmarks = await asyncio.gather(
            snapshot_task, *benchmark_tasks, return_exceptions=True
        )
        if isinstance(snapshot, BaseException):
            return "The daily brief could not be generated because portfolio data is unavailable."
        flags = build_risk_flags(snapshot)
        lines = [
            f"☀️ DAILY PORTFOLIO BRIEF • {now:%b %d, %Y %I:%M %p %Z}",
            "",
            f"Tracked value: {money(snapshot.total_value)}",
            f"Latest session: {money(snapshot.day_change)} ({percent(snapshot.day_change_pct)})",
            f"Since average cost: {money(snapshot.total_gain_loss)} "
            f"({percent(snapshot.total_gain_loss_pct)})",
            "",
            "MARKET PULSE",
        ]
        for symbol, benchmark in zip(("SPY", "QQQ", "IWM"), benchmarks, strict=True):
            if isinstance(benchmark, BaseException):
                lines.append(f"{symbol}: unavailable")
            else:
                lines.append(
                    f"{symbol}: {money(benchmark.current_price)} "
                    f"({percent(benchmark.day_change_pct)})"
                )

        lines.extend(["", "WHAT NEEDS REVIEW"])
        for flag in flags[:4]:
            icon = {"HIGH": "🔴", "MEDIUM": "🟡", "INFO": "🔵"}[flag.severity]
            lines.append(f"{icon} {flag.title}: {flag.detail}")

        if snapshot.holdings:
            movers = sorted(
                snapshot.holdings, key=lambda item: abs(item.day_change_pct), reverse=True
            )
            lines.extend(["", "TOP POSITION MOVES"])
            for holding in movers[:3]:
                lines.append(
                    f"{holding.ticker}: {percent(holding.day_change_pct)} • "
                    f"{holding.portfolio_weight_pct:.1f}% weight"
                )
        lines.extend(
            [
                "",
                self._data_notice(snapshot),
                "Use /risk for details or /analyze TICKER for technical context.",
                "Educational decision support only. No order was or can be placed.",
            ]
        )
        return truncate_message("\n".join(lines))

    async def tip_text(self, user_id: int) -> str:
        snapshot = await self.snapshot(user_id)
        flags = build_risk_flags(snapshot)
        first = flags[0]
        if "concentration" in first.title.lower() or "position size" in first.title.lower():
            tip = (
                "Write down a maximum position percentage before the market moves. A prewritten "
                "rule is easier to follow than a decision made during a fast price swing."
            )
        elif "thesis" in first.title.lower():
            tip = (
                "A falling price is not a complete sell rule. Recheck revenue, margins, debt, the "
                "original catalyst, and the condition that would prove your thesis wrong."
            )
        elif "data" in first.title.lower():
            tip = "Do not make a portfolio decision while key prices or position data are missing."
        else:
            tip = (
                "Compare every new idea with the best use of the same dollar: cash reserve, debt, "
                "a diversified fund, or an existing high-conviction holding."
            )
        return f"💡 PORTFOLIO HABIT\n\n{tip}\n\nThis is general education, not a trade instruction."

    @staticmethod
    def _format_security_analysis(analysis: SecurityAnalysis) -> str:
        lines = [
            f"🔎 {analysis.ticker} REVIEW",
            "",
            f"Context: {analysis.label}",
            f"Price: {money(analysis.current_price)}",
            f"Latest session: {percent(analysis.day_change_pct)}",
            f"20-session momentum: {percent(analysis.momentum_20d_pct)}",
            f"20-session average: {number(analysis.moving_average_20d)}",
            f"50-session average: {number(analysis.moving_average_50d)}",
            f"Annualized historical volatility: {percent(analysis.annualized_volatility_pct)}",
            f"Maximum drawdown in loaded history: {percent(analysis.max_drawdown_pct)}",
            f"RSI(14): {number(analysis.rsi_14d)}",
            "",
            "How to use this:",
            "• Compare the trend with company fundamentals and upcoming events.",
            "• Check how much portfolio concentration the position would create.",
            "• Define the thesis and invalidation condition before acting.",
            "",
            f"Data: {analysis.market.provider} • {analysis.market.as_of:%Y-%m-%d %H:%M UTC}",
            "Technical context is not a buy or sell recommendation.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _data_notice(snapshot: PortfolioSnapshot) -> str:
        if not snapshot.holdings:
            return "Data: no priced holdings"
        newest = max(holding.market.as_of for holding in snapshot.holdings)
        providers = sorted({holding.market.provider for holding in snapshot.holdings})
        return f"Data: {', '.join(providers)} • latest timestamp {newest:%Y-%m-%d %H:%M UTC}"
