from __future__ import annotations


def number_text(value: int | float | None) -> str:
    if value is None:
        return "-"
    return str(value)
