from __future__ import annotations

from decimal import Decimal

from portfolio_bot.database import Database


def registered_database(tmp_path) -> Database:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.register_user(1, 1, "One", "UTC", "07:30")
    database.register_user(2, 2, "Two", "UTC", "07:30")
    return database


def test_holding_weighted_average_and_tenant_isolation(tmp_path) -> None:
    database = registered_database(tmp_path)
    database.add_holding(1, "AAPL", Decimal("10"), Decimal("100"))
    result = database.add_holding(1, "AAPL", Decimal("10"), Decimal("200"))

    assert result.quantity == Decimal("20")
    assert result.average_cost == Decimal("150")
    assert database.list_holdings(2) == []


def test_delete_user_cascades_portfolio_data(tmp_path) -> None:
    database = registered_database(tmp_path)
    database.set_cash(1, Decimal("500"))
    database.set_holding(1, "MSFT", Decimal("2"), Decimal("400"))
    database.add_watch(1, "NVDA")

    database.delete_user(1)

    assert database.get_user(1) is None
    assert database.list_holdings(1) == []
    assert database.list_watchlist(1) == []
    assert database.get_cash(1) == Decimal("0")


def test_database_releases_file_handles(tmp_path) -> None:
    database_path = tmp_path / "handles.sqlite3"
    database = Database(database_path)
    database.initialize()
    database.register_user(1, 1, "One", "UTC", "07:30")

    database_path.unlink()

    assert not database_path.exists()
