from __future__ import annotations

from datetime import date


def period_start(target_date: date) -> date:
    return target_date.replace(day=1)


def period_end(current_period_start: date) -> date:
    if current_period_start.month == 12:
        return date.fromordinal(date(current_period_start.year + 1, 1, 1).toordinal() - 1)
    return date.fromordinal(
        date(current_period_start.year, current_period_start.month + 1, 1).toordinal() - 1
    )


__all__ = ["period_end", "period_start"]
