from __future__ import annotations

from datetime import date


def format_period_label(period_start: date) -> str:
    return period_start.strftime("%b %Y")


__all__ = ["format_period_label"]
