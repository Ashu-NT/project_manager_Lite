"""Percent formatting helpers."""

from __future__ import annotations


def format_percent(value: float | None, *, fallback: str = "0.0%") -> str:
    if value is None:
        return fallback
    return f"{float(value):.1f}%"


def format_signed_percent(value: float | None) -> str:
    if value is None:
        return "0.0%"
    return f"{float(value):+.1f}%"


def format_signed_int(value: int | None) -> str:
    return f"{int(value or 0):+d}"


__all__ = ["format_percent", "format_signed_int", "format_signed_percent"]
