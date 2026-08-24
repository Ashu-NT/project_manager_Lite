from __future__ import annotations

from src.core.platform.finance.money.currency import ISO_4217_MINOR_UNITS


DEFAULT_CURRENCY_CODE = "XAF"
CURRENCY_OPTIONS: list[dict[str, str]] = [
    {"value": code, "label": code}
    for code in sorted(
        code for code, minor_units in ISO_4217_MINOR_UNITS.items() if minor_units is not None
    )
]


__all__ = ["CURRENCY_OPTIONS", "DEFAULT_CURRENCY_CODE"]
