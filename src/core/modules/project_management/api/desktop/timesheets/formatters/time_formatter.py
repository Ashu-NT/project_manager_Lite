from __future__ import annotations


def format_hours(value: float | None) -> str:
    return f"{float(value or 0.0):.2f}h"


__all__ = ["format_hours"]
