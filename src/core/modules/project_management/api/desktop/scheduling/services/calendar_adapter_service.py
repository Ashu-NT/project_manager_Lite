"""Platform calendar integration helpers."""


class _DefaultCalendar:
    id = "default"
    name = "Global Calendar"
    working_days = {0, 1, 2, 3, 4}
    hours_per_day = 8.0


def get_legacy_calendar(work_calendar_service=None):
    if work_calendar_service is not None:
        return work_calendar_service.get_calendar()
    return _DefaultCalendar()


def list_legacy_holidays(work_calendar_service=None) -> list:
    if work_calendar_service is None:
        return []
    return work_calendar_service.list_holidays()


def unwrap_platform_calendar_result(result):
    if bool(getattr(result, "ok", False)):
        return getattr(result, "data", None)
    error = getattr(result, "error", None)
    category = str(getattr(error, "category", "") or "").strip().lower()
    message = str(getattr(error, "message", "") or "Platform calendar operation failed.")
    if category == "validation":
        raise ValueError(message)
    if category == "permission":
        raise PermissionError(message)
    if message:
        raise RuntimeError(message)
    raise RuntimeError("Platform calendar operation failed.")


__all__ = ["get_legacy_calendar", "list_legacy_holidays", "unwrap_platform_calendar_result"]
