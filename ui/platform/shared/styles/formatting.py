from __future__ import annotations


def fmt_int(value: int | None) -> str:
    if value is None:
        return "-"
    return f"{int(value):,}"


def fmt_float(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "-"
    fmt = f"{{:,.{decimals}f}}"
    return fmt.format(float(value))


def fmt_percent(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "-"
    fmt = f"{{:.{decimals}f}} %"
    return fmt.format(float(value))


def fmt_currency(value: float | None, currency_symbol: str = "") -> str:
    if value is None:
        return "-"
    return f"{currency_symbol} {fmt_float(value, 2)}".strip()


CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "EUR",
    "GBP": "GBP",
    "JPY": "JPY",
    "XAF": "F.CFA",
}


def currency_symbol_from_code(code: str | None) -> str:
    if not code:
        return ""
    return CURRENCY_SYMBOLS.get(code.upper(), "")


def fmt_money(x: float | None) -> str:
    if x is None:
        return "-"
    return f"{x:,.2f}"


def fmt_ratio(x: float | None) -> str:
    if x is None:
        return "-"
    return f"{x:.2f}"
