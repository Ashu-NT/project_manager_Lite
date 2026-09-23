from __future__ import annotations

_WEEKDAY_ABBREVIATIONS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def working_week_label(working_weekdays: tuple[int, ...]) -> str:
    days = sorted(d for d in working_weekdays if 0 <= d <= 6)
    if not days:
        return "No working days configured"
    if len(days) == 7:
        return "Every day"
    if days == list(range(days[0], days[-1] + 1)):
        return f"{_WEEKDAY_ABBREVIATIONS[days[0]]}–{_WEEKDAY_ABBREVIATIONS[days[-1]]}"
    return ", ".join(_WEEKDAY_ABBREVIATIONS[d] for d in days)


def holiday_set_label(locale: str, holiday_count: int) -> str:
    if locale:
        return locale
    if holiday_count > 0:
        return f"{holiday_count} holiday{'s' if holiday_count != 1 else ''} configured"
    return "No holidays configured"


__all__ = ["holiday_set_label", "working_week_label"]
