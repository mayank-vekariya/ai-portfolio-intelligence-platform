from __future__ import annotations

import asyncio
import math
import re
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from urllib.parse import quote

import httpx

TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")


class MarketDataError(RuntimeError):
    """Raised when a provider cannot supply usable market data."""


def normalize_ticker(raw: str) -> str:
    ticker = raw.strip().upper()
    if not TICKER_PATTERN.fullmatch(ticker):
        raise ValueError("Ticker must contain only letters, numbers, dots, or hyphens")
    return ticker


@dataclass(frozen=True)
class DailyBar:
    day: date
    close: Decimal


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    current_price: Decimal
    previous_close: Decimal
    currency: str
    as_of: datetime
    history: tuple[DailyBar, ...]
    provider: str
    prototype_only: bool

    @property
    def day_change(self) -> Decimal:
        return self.current_price - self.previous_close

    @property
    def day_change_pct(self) -> Decimal:
        if self.previous_close == 0:
            return Decimal("0")
        return (self.day_change / self.previous_close) * Decimal("100")


class MarketDataProvider(Protocol):
    async def get_snapshot(self, ticker: str) -> MarketSnapshot: ...


class YahooPrototypeProvider:
    """Development-only provider using an unofficial public chart endpoint.

    Replace this adapter with a licensed commercial provider before a public beta.
    """

    base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    async def get_snapshot(self, ticker: str) -> MarketSnapshot:
        symbol = normalize_ticker(ticker)
        provider_symbol = symbol.replace(".", "-")
        url = f"{self.base_url}/{quote(provider_symbol, safe='')}"
        params = {"range": "6mo", "interval": "1d", "events": "div,splits"}
        headers = {"User-Agent": "PortfolioTelegramBot/0.1 prototype"}
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
            chart = payload.get("chart", {})
            if chart.get("error"):
                raise MarketDataError(str(chart["error"]))
            result = chart.get("result") or []
            if not result:
                raise MarketDataError(f"No market data returned for {symbol}")
            item = result[0]
            meta = item.get("meta", {})
            timestamps = item.get("timestamp") or []
            indicators = item.get("indicators", {})
            adjusted = (indicators.get("adjclose") or [{}])[0].get("adjclose") or []
            closes = adjusted or (indicators.get("quote") or [{}])[0].get("close") or []
            history = tuple(
                DailyBar(
                    day=datetime.fromtimestamp(timestamp, tz=UTC).date(),
                    close=Decimal(str(close)),
                )
                for timestamp, close in zip(timestamps, closes, strict=False)
                if close is not None
            )
            current_value = meta.get("regularMarketPrice")
            if current_value is None and history:
                current_value = history[-1].close
            previous_value = meta.get("regularMarketPreviousClose") or meta.get(
                "chartPreviousClose"
            )
            if previous_value is None and len(history) >= 2:
                previous_value = history[-2].close
            if current_value is None or previous_value is None:
                raise MarketDataError(f"Incomplete market data returned for {symbol}")
            market_time = meta.get("regularMarketTime")
            as_of = (
                datetime.fromtimestamp(market_time, tz=UTC) if market_time else datetime.now(tz=UTC)
            )
            return MarketSnapshot(
                symbol=symbol,
                current_price=Decimal(str(current_value)),
                previous_close=Decimal(str(previous_value)),
                currency=str(meta.get("currency") or "USD"),
                as_of=as_of,
                history=history,
                provider="Yahoo prototype feed",
                prototype_only=True,
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            if isinstance(exc, MarketDataError):
                raise
            raise MarketDataError(f"Could not load market data for {symbol}") from exc


class MockMarketDataProvider:
    async def get_snapshot(self, ticker: str) -> MarketSnapshot:
        symbol = normalize_ticker(ticker)
        await asyncio.sleep(0)
        anchor = Decimal(str(40 + (sum(ord(char) for char in symbol) % 240)))
        today = datetime.now(tz=UTC).date()
        bars: list[DailyBar] = []
        for index in range(90):
            drift = Decimal(index) * Decimal("0.0015")
            wave = Decimal(str(math.sin(index / 5) * 0.025))
            close = (anchor * (Decimal("1") + drift + wave)).quantize(Decimal("0.01"))
            bars.append(DailyBar(day=today - timedelta(days=89 - index), close=close))
        return MarketSnapshot(
            symbol=symbol,
            current_price=bars[-1].close,
            previous_close=bars[-2].close,
            currency="USD",
            as_of=datetime.now(tz=UTC),
            history=tuple(bars),
            provider="Deterministic fixture data",
            prototype_only=True,
        )


class CachingMarketDataProvider:
    def __init__(self, wrapped: MarketDataProvider, ttl_seconds: int = 300) -> None:
        self.wrapped = wrapped
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, MarketSnapshot]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_snapshot(self, ticker: str) -> MarketSnapshot:
        symbol = normalize_ticker(ticker)
        cached = self._cache.get(symbol)
        now = time.monotonic()
        if cached and now - cached[0] <= self.ttl_seconds:
            return cached[1]
        lock = self._locks.setdefault(symbol, asyncio.Lock())
        async with lock:
            cached = self._cache.get(symbol)
            now = time.monotonic()
            if cached and now - cached[0] <= self.ttl_seconds:
                return cached[1]
            snapshot = await self.wrapped.get_snapshot(symbol)
            self._cache[symbol] = (time.monotonic(), snapshot)
            return snapshot


def build_market_provider(name: str, cache_seconds: int) -> MarketDataProvider:
    provider: MarketDataProvider
    if name == "mock":
        provider = MockMarketDataProvider()
    elif name == "yahoo":
        provider = YahooPrototypeProvider()
    else:
        raise ValueError(f"Unknown market data provider: {name}")
    return CachingMarketDataProvider(provider, ttl_seconds=cache_seconds)
