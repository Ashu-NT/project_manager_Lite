from __future__ import annotations

from src.core.platform.time.domain import TimesheetPeriodStatus


def coerce_queue_status(value: str) -> TimesheetPeriodStatus | None:
    normalized_value = str(value or "all").strip().upper()
    if not normalized_value or normalized_value == "ALL":
        return None
    try:
        return TimesheetPeriodStatus(normalized_value)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported timesheet queue status: {normalized_value}."
        ) from exc


__all__ = ["coerce_queue_status"]
