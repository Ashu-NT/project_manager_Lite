from __future__ import annotations


def yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def money_text(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"
