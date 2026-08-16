from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class UserRecord:
    telegram_user_id: int
    chat_id: int
    display_name: str
    timezone: str
    daily_brief_time: str
    daily_brief_enabled: bool


@dataclass(frozen=True)
class Holding:
    ticker: str
    quantity: Decimal
    average_cost: Decimal


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    telegram_user_id INTEGER PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    display_name TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    daily_brief_time TEXT NOT NULL,
                    daily_brief_enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS portfolio_cash (
                    user_id INTEGER PRIMARY KEY,
                    amount TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS holdings (
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    average_cost TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, ticker),
                    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS watchlist (
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, ticker),
                    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id) ON DELETE CASCADE
                );

                PRAGMA user_version = 1;
                """
            )

    def register_user(
        self,
        telegram_user_id: int,
        chat_id: int,
        display_name: str,
        timezone: str,
        daily_brief_time: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (
                    telegram_user_id, chat_id, display_name, timezone, daily_brief_time
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    chat_id = excluded.chat_id,
                    display_name = excluded.display_name,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (telegram_user_id, chat_id, display_name[:100], timezone, daily_brief_time),
            )

    def get_user(self, telegram_user_id: int) -> UserRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,)
            ).fetchone()
        if row is None:
            return None
        return UserRecord(
            telegram_user_id=row["telegram_user_id"],
            chat_id=row["chat_id"],
            display_name=row["display_name"],
            timezone=row["timezone"],
            daily_brief_time=row["daily_brief_time"],
            daily_brief_enabled=bool(row["daily_brief_enabled"]),
        )

    def list_active_users(self) -> list[UserRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM users WHERE daily_brief_enabled = 1 ORDER BY telegram_user_id"
            ).fetchall()
        return [
            UserRecord(
                telegram_user_id=row["telegram_user_id"],
                chat_id=row["chat_id"],
                display_name=row["display_name"],
                timezone=row["timezone"],
                daily_brief_time=row["daily_brief_time"],
                daily_brief_enabled=bool(row["daily_brief_enabled"]),
            )
            for row in rows
        ]

    def set_daily_schedule(
        self, telegram_user_id: int, daily_time: str, timezone: str, enabled: bool = True
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET daily_brief_time = ?, timezone = ?, daily_brief_enabled = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE telegram_user_id = ?
                """,
                (daily_time, timezone, int(enabled), telegram_user_id),
            )

    def set_daily_enabled(self, telegram_user_id: int, enabled: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE users SET daily_brief_enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_user_id = ?
                """,
                (int(enabled), telegram_user_id),
            )

    def set_cash(self, telegram_user_id: int, amount: Decimal) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO portfolio_cash (user_id, amount) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    amount = excluded.amount, updated_at = CURRENT_TIMESTAMP
                """,
                (telegram_user_id, format(amount, "f")),
            )

    def get_cash(self, telegram_user_id: int) -> Decimal:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT amount FROM portfolio_cash WHERE user_id = ?", (telegram_user_id,)
            ).fetchone()
        return Decimal(row["amount"]) if row else Decimal("0")

    def add_holding(
        self, telegram_user_id: int, ticker: str, quantity: Decimal, average_cost: Decimal
    ) -> Holding:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT quantity, average_cost FROM holdings WHERE user_id = ? AND ticker = ?",
                (telegram_user_id, ticker),
            ).fetchone()
            if row:
                old_quantity = Decimal(row["quantity"])
                old_cost = Decimal(row["average_cost"])
                new_quantity = old_quantity + quantity
                new_cost = ((old_quantity * old_cost) + (quantity * average_cost)) / new_quantity
            else:
                new_quantity = quantity
                new_cost = average_cost
            connection.execute(
                """
                INSERT INTO holdings (user_id, ticker, quantity, average_cost)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, ticker) DO UPDATE SET
                    quantity = excluded.quantity,
                    average_cost = excluded.average_cost,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    telegram_user_id,
                    ticker,
                    format(new_quantity, "f"),
                    format(new_cost, "f"),
                ),
            )
        return Holding(ticker=ticker, quantity=new_quantity, average_cost=new_cost)

    def set_holding(
        self, telegram_user_id: int, ticker: str, quantity: Decimal, average_cost: Decimal
    ) -> Holding:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO holdings (user_id, ticker, quantity, average_cost)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, ticker) DO UPDATE SET
                    quantity = excluded.quantity,
                    average_cost = excluded.average_cost,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    telegram_user_id,
                    ticker,
                    format(quantity, "f"),
                    format(average_cost, "f"),
                ),
            )
        return Holding(ticker=ticker, quantity=quantity, average_cost=average_cost)

    def remove_holding(self, telegram_user_id: int, ticker: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM holdings WHERE user_id = ? AND ticker = ?",
                (telegram_user_id, ticker),
            )
        return cursor.rowcount > 0

    def list_holdings(self, telegram_user_id: int) -> list[Holding]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ticker, quantity, average_cost FROM holdings
                WHERE user_id = ? ORDER BY ticker
                """,
                (telegram_user_id,),
            ).fetchall()
        return [
            Holding(
                ticker=row["ticker"],
                quantity=Decimal(row["quantity"]),
                average_cost=Decimal(row["average_cost"]),
            )
            for row in rows
        ]

    def add_watch(self, telegram_user_id: int, ticker: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO watchlist (user_id, ticker) VALUES (?, ?)",
                (telegram_user_id, ticker),
            )

    def remove_watch(self, telegram_user_id: int, ticker: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
                (telegram_user_id, ticker),
            )
        return cursor.rowcount > 0

    def list_watchlist(self, telegram_user_id: int) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY ticker",
                (telegram_user_id,),
            ).fetchall()
        return [row["ticker"] for row in rows]

    def delete_user(self, telegram_user_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM users WHERE telegram_user_id = ?", (telegram_user_id,))
