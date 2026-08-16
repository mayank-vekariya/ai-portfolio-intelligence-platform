from __future__ import annotations

import pytest

from portfolio_bot.config import ConfigurationError, parse_allowed_user_ids, parse_clock


def test_allowed_user_ids() -> None:
    assert parse_allowed_user_ids("123, 456") == frozenset({123, 456})
    assert parse_allowed_user_ids("") is None


def test_allowed_user_ids_reject_text() -> None:
    with pytest.raises(ConfigurationError):
        parse_allowed_user_ids("123,not-a-number")


def test_parse_clock_uses_timezone() -> None:
    result = parse_clock("07:30", "America/Los_Angeles")
    assert result.hour == 7
    assert result.minute == 30
    assert result.tzinfo is not None


def test_parse_clock_rejects_invalid_input() -> None:
    with pytest.raises(ConfigurationError):
        parse_clock("25:99", "America/Los_Angeles")
