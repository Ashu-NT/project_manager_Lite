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


_SOURCE_PREFIX_LEVEL_NAME = {
    "GLOBAL": "Organization",
    "SITE": "Site",
    "DEPT": "Department",
    "EMP": "Employee",
    "PRJ": "Project",
    "RESOURCE": "Resource",
}


def canonical_source_label(source_label: str, *, own_prefix: str) -> str:
    """Translate the resolver's internal winning-chain label (e.g. "GLOBAL",
    "SITE-ABC123", "EMP-XYZ" -- see EnterpriseCalendarResolver.
    resolve_effective_calendar) into the one canonical, human-readable
    vocabulary every Calendar summary card must share (never let each page
    invent its own wording):

        Organization default / Site override / Department override /
        Employee override                    -- the level resolved its OWN
                                                 direct assignment
        Inherited from Organization / Site / Department
                                              -- resolved from a different,
                                                 higher level

    Calendar NAME and inheritance SOURCE are always two separate concepts
    -- this function only ever returns the source half.
    """
    if not source_label:
        return ""
    prefix = source_label.split("-", 1)[0]
    level_name = _SOURCE_PREFIX_LEVEL_NAME.get(prefix, prefix.title())
    if prefix == own_prefix:
        return "Organization default" if prefix == "GLOBAL" else f"{level_name} override"
    return f"Inherited from {level_name}"


__all__ = ["canonical_source_label", "holiday_set_label", "working_week_label"]
