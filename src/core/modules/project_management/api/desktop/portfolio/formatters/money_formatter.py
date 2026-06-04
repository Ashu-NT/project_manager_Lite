"""Money formatting helpers."""

from __future__ import annotations


def format_money(value: float | None, *, fallback: str = "0.00") -> str:
    if value is None:
        return fallback
    return f"{float(value):,.2f}"


def format_signed_money(value: float | None) -> str:
    if value is None:
        return "0.00"
    return f"{float(value):+,.2f}"


__all__ = ["format_money", "format_signed_money"]
