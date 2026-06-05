from __future__ import annotations


def format_money(value: float | None, currency: str | None) -> str:
    amount = float(value or 0.0)
    resolved_currency = (currency or "").strip().upper()
    if resolved_currency:
        return f"{resolved_currency} {amount:,.2f}"
    return f"{amount:,.2f}"


__all__ = ["format_money"]
