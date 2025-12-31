# ui/formatting.py
from __future__ import annotations

def fmt_int(value: int | None) -> str:
    """
    Format integer with thousands separator.
    Example: 1234567 -> '1,234,567'
    """
    if value is None:
        return "-"
    return f"{int(value):,}"

def fmt_float(value: float | None, decimals: int = 2) -> str:
    """
    Format float with thousands separator and fixed decimals.
    Example: 1234567.8 -> '1,234,567.80'
    """
    if value is None:
        return "-"
    fmt = f"{{:,.{decimals}f}}"
    return fmt.format(float(value))

def fmt_percent(value: float | None, decimals: int = 1) -> str:
    """
    Format percent value (0–100) with % sign.
    Example: 75.3 -> '75.3 %'
    """
    if value is None:
        return "-"
    fmt = f"{{:.{decimals}f}} %"
    return fmt.format(float(value))

def fmt_currency(value: float | None, currency_symbol: str = "") -> str:
    """
    Format currency with thousands and 2 decimals.
    Example: 1234567.8, '€' -> '€ 1,234,567.80'
    """
    if value is None:
        return "-"
    return f"{currency_symbol} {fmt_float(value, 2)}".strip()

# Simple dictionary of currency codes to symbols
CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "XAF": "F.CFA",   # Central African CFA Franc
}

def currency_symbol_from_code(code: str | None) -> str:
    if not code:
        return ""   # fallback if no code provided
    return CURRENCY_SYMBOLS.get(code.upper(), "")

def fmt_money(x: float | None) -> str:
    if x is None:
        return "-"
    return f"{x:,.2f}"

def fmt_ratio(x: float | None) -> str:
    if x is None:
        return "-"
    return f"{x:.2f}"