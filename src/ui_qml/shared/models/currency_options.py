from __future__ import annotations

import pycountry

from src.core.platform.domain.finance.money.currency import ISO_4217_MINOR_UNITS


DEFAULT_CURRENCY_CODE = "XAF"


def currency_name_for_code(code: str) -> str:
    """
    Return the ISO currency display name for `code`.

    Unknown codes return an empty string so callers can safely
    fall back to displaying the raw code.
    """
    normalized = str(code or "").strip().upper()

    if not normalized:
        return ""

    currency = pycountry.currencies.get(alpha_3=normalized)

    return currency.name if currency is not None else ""


def currency_label(code: str) -> str:
    """
    Human-readable dropdown label.

    Examples:
        EUR -> "EUR - Euro"
        XAF -> "XAF - CFA Franc BEAC"

    Unknown codes remain visible as their raw code.
    """
    normalized = str(code or "").strip().upper()

    if not normalized:
        return ""

    name = currency_name_for_code(normalized)

    return f"{normalized} - {name}" if name else normalized


CURRENCY_OPTIONS: tuple[dict[str, str], ...] = tuple(
    {
        "value": code,
        "label": currency_label(code),
    }
    for code in sorted(
        code
        for code, minor_units in ISO_4217_MINOR_UNITS.items()
        if minor_units is not None
    )
)


__all__ = [
    "CURRENCY_OPTIONS",
    "DEFAULT_CURRENCY_CODE",
    "currency_label",
    "currency_name_for_code",
]