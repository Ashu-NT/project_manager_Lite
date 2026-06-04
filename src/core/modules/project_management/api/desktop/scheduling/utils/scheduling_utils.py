"""Scheduling display and computation utilities."""


def remaining_duration_days(duration_days: int | None, percent_complete: float) -> int | None:
    if duration_days is None:
        return None
    remaining_ratio = max(0.0, 1.0 - (float(percent_complete or 0.0) / 100.0))
    return max(0, int(round(duration_days * remaining_ratio)))


__all__ = ["remaining_duration_days"]
