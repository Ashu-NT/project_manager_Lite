from __future__ import annotations

import pytest

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_budget,
    format_decimal_amount,
    format_hourly_rate,
    format_money,
    format_signed_money,
)
from src.core.platform.common.exceptions import ValidationError


def test_financial_formatting_uses_decimal_rounding_and_currency_minor_units() -> None:
    assert format_money("1234.565", "EUR") == "EUR 1,234.56"
    assert format_money("125.5", "JPY") == "JPY 126"
    assert format_money("1.2345", "BHD") == "BHD 1.234"
    assert format_signed_money("-12.5") == "-12.50"
    assert format_decimal_amount("12.50", grouping=False) == "12.50"


def test_financial_formatting_preserves_desktop_fallback_contracts() -> None:
    assert format_budget(None, "EUR") == "No approved budget"
    assert format_hourly_rate(None, "EUR") == "Rate not set"
    assert format_money(None, fallback="No limit") == "No limit"
    assert format_money("12.5", "USD") == "USD 12.50"


def test_financial_formatting_rejects_binary_float() -> None:
    with pytest.raises(ValidationError) as exc:
        format_money(12.5, "USD")  # type: ignore[arg-type]
    assert exc.value.code == "DECIMAL_BINARY_FLOAT_FORBIDDEN"


def test_financial_formatting_rejects_invalid_currency() -> None:
    with pytest.raises(ValidationError) as exc:
        format_money("10", "ZZZ")
    assert exc.value.code == "CURRENCY_CODE_INVALID"
