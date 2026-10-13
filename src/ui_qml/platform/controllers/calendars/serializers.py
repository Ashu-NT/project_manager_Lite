from __future__ import annotations

from datetime import date as _date

from src.core.platform.application.time_management.calendar.definitions.recurrence_text import (
    humanize_rrule,
)

_IMPACT_LABELS: dict[str, str] = {
    "UNAVAILABLE": "Non-working",
    "REDUCED_CAPACITY": "Reduced capacity",
    "EXTRA_CAPACITY": "Extra working",
    "WORKING": "Extra working",
    "INFORMATION_ONLY": "Information",
}
_IMPACT_TONES: dict[str, str] = {
    "UNAVAILABLE": "unavailable",
    "REDUCED_CAPACITY": "reduced",
    "EXTRA_CAPACITY": "extra",
    "WORKING": "extra",
    "INFORMATION_ONLY": "info",
}
# Shared `AppWidgets.StatusChip` tone vocabulary (neutral/info/success/
# warning/danger) -- distinct from _IMPACT_TONES above, which feeds the
# Month grid's own custom cell tone system, not a StatusChip.
_IMPACT_STATUS_CHIP_TONES: dict[str, str] = {
    "UNAVAILABLE": "danger",
    "REDUCED_CAPACITY": "warning",
    "EXTRA_CAPACITY": "success",
    "WORKING": "success",
    "INFORMATION_ONLY": "info",
}
_APPROVAL_STATUS_CHIP_TONES: dict[str, str] = {
    "APPROVED": "success",
    "PENDING": "warning",
    "REJECTED": "danger",
}


def _human_label(enum_value: str) -> str:
    text = str(enum_value or "").replace("_", " ").strip().lower()
    return text[:1].upper() + text[1:] if text else ""


def _format_hhmm(value: str) -> str:
    # Desktop API time strings are already "HH:MM"; this just guards against
    # an empty/unset value rather than reformatting a real one.
    return str(value or "").strip()


def _title_case_label(enum_value: str) -> str:
    """Generic enum -> display label for the Exceptions/Recurring table and
    Inspector contexts (e.g. "REDUCED_CAPACITY" -> "Reduced Capacity"). The
    Month view's own `_human_label` above deliberately diverges for a few
    values ("Non-working" reads better in a tiny grid cell than the literal
    "Unavailable") -- this is the literal, generic translation used wherever
    the enum's own meaning should be shown as-is."""
    text = str(enum_value or "").replace("_", " ").strip()
    return text.title() if text else ""


def _format_date_label(iso_date: str) -> str:
    if not iso_date:
        return ""
    try:
        parsed = _date.fromisoformat(iso_date)
    except ValueError:
        return iso_date
    return parsed.strftime("%d %b %Y")


def serialize_calendar_day_view(day, *, today_iso: str) -> dict[str, object]:
    """One Month-view cell's full read projection, built once per range fetch
    -- never recomputed per QML binding. `tone`/labels are derived here (not
    in QML) from the backend-resolved CalendarDayDto fields only; isToday
    compares against the calendar's own business-local today (passed in),
    never a QML `new Date()`. isCurrentMonth/isSelected are left to QML since
    they depend on which month page/day is currently displayed -- pure view
    state, not calendar business logic."""
    date_str = str(getattr(day, "date", "") or "")
    is_working_day = bool(getattr(day, "is_working_day", False))
    available_hours = float(getattr(day, "available_hours", 0.0) or 0.0)
    start_time = _format_hhmm(getattr(day, "start_time", ""))
    end_time = _format_hhmm(getattr(day, "end_time", ""))
    exception_type = str(getattr(day, "exception_type", "") or "")
    exception_name = str(getattr(day, "exception_name", "") or "")
    impact_type = str(getattr(day, "impact_type", "") or "")

    hours_label = f"{start_time}–{end_time}" if start_time and end_time else ""
    impact_label = _IMPACT_LABELS.get(impact_type, "")
    # Holiday gets its own calm, distinct tone rather than the same
    # muted/alarming treatment as a generic UNAVAILABLE closure -- both are
    # ImpactType.UNAVAILABLE under the hood, but a public holiday and an
    # ad-hoc site shutdown read very differently to an admin scanning a month.
    if exception_type == "HOLIDAY":
        tone = "holiday"
    else:
        tone = _IMPACT_TONES.get(impact_type, "normal" if is_working_day else "nonWorking")

    if impact_type:
        primary_label = exception_name or _human_label(exception_type) or impact_label
        secondary_label = impact_label if impact_type != "INFORMATION_ONLY" else hours_label
        if impact_type in ("EXTRA_CAPACITY", "WORKING") and hours_label:
            secondary_label = hours_label
    elif is_working_day:
        primary_label = hours_label
        secondary_label = ""
    else:
        primary_label = "Non-working"
        secondary_label = ""

    try:
        parsed = _date.fromisoformat(date_str) if date_str else None
    except ValueError:
        parsed = None
    day_number = parsed.day if parsed else 0
    date_label = parsed.strftime("%A, %d %B %Y") if parsed else date_str

    accessibility_parts = [date_label]
    if impact_label:
        accessibility_parts.append(impact_label)
    elif is_working_day:
        accessibility_parts.append("Working day")
    else:
        accessibility_parts.append("Non-working")
    if is_working_day and available_hours > 0:
        hours_word = "hour" if available_hours == 1 else "hours"
        accessibility_parts.append(f"{available_hours:g} available {hours_word}")
    if exception_name:
        accessibility_parts.append(exception_name)

    return {
        "date": date_str,
        "dayNumber": day_number,
        "dateLabel": date_label,
        "isToday": date_str == today_iso,
        "isWorkingDay": is_working_day,
        "availableHours": available_hours,
        "startTimeLabel": start_time,
        "endTimeLabel": end_time,
        "primaryLabel": primary_label,
        "secondaryLabel": secondary_label,
        "exceptionTypeLabel": _human_label(exception_type),
        "impactLabel": impact_label,
        "tone": tone,
        "accessibilityLabel": ". ".join(accessibility_parts) + ".",
    }


def serialize_calendar_assignment(assignment, *, entity_name: str = "") -> dict[str, object]:
    if assignment is None:
        return {}
    return {
        "assignmentId": str(getattr(assignment, "id", "") or ""),
        "entityType": str(getattr(assignment, "entity_type", "") or ""),
        "entityId": str(getattr(assignment, "entity_id", "") or ""),
        "entityName": entity_name,
        "calendarId": str(getattr(assignment, "calendar_id", "") or ""),
        "calendarName": str(getattr(assignment, "calendar_name", "") or ""),
        "calendarType": str(getattr(assignment, "calendar_type", "") or ""),
        "isDefault": bool(getattr(assignment, "is_default", False)),
        "priority": int(getattr(assignment, "priority", 0) or 0),
        "effectiveFrom": str(getattr(assignment, "effective_from", "") or ""),
        "effectiveTo": str(getattr(assignment, "effective_to", "") or ""),
    }


def serialize_assignment_groups(
    assignments: object, *, name_lookup: dict[str, dict[str, str]] | None = None
) -> dict[str, object]:
    """`name_lookup` maps group name ("sites"/"departments"/"employees") to
    an {entityId: displayName} dict -- built from the Platform entity
    catalogs already loaded in memory for the admin workspace (no extra
    query). Projects/Resources are PM-owned; Platform has no approved
    cross-module contract to resolve their display names, so those groups
    are left with entityId only rather than importing PM internals."""
    from .context import empty_calendar_detail_context
    if not isinstance(assignments, dict):
        return empty_calendar_detail_context()["assignments"]
    lookup = name_lookup or {}

    def _group(key: str) -> list[dict[str, object]]:
        names = lookup.get(key, {})
        return [
            serialize_calendar_assignment(
                item, entity_name=names.get(str(getattr(item, f"{key[:-1]}_id" if key != "employees" else "employee_id", "") or getattr(item, "entity_id", "") or ""), "")
            )
            for item in assignments.get(key, ())
        ]

    return {
        "sites": [
            serialize_calendar_assignment(item, entity_name=lookup.get("sites", {}).get(str(getattr(item, "entity_id", "") or ""), ""))
            for item in assignments.get("sites", ())
        ],
        "departments": [
            serialize_calendar_assignment(item, entity_name=lookup.get("departments", {}).get(str(getattr(item, "entity_id", "") or ""), ""))
            for item in assignments.get("departments", ())
        ],
        "employees": [
            serialize_calendar_assignment(item, entity_name=lookup.get("employees", {}).get(str(getattr(item, "entity_id", "") or ""), ""))
            for item in assignments.get("employees", ())
        ],
        "projects": [
            serialize_calendar_assignment(item) for item in assignments.get("projects", ())
        ],
        "resources": [
            serialize_calendar_assignment(item) for item in assignments.get("resources", ())
        ],
    }


def serialize_working_rule(rule) -> dict[str, object]:
    return {
        "id": str(getattr(rule, "id", "") or ""),
        "weekday": int(getattr(rule, "weekday", 0) or 0),
        "isWorkingDay": bool(getattr(rule, "is_working_day", False)),
        "startTime": str(getattr(rule, "start_time", "") or ""),
        "endTime": str(getattr(rule, "end_time", "") or ""),
        "breakStartTime": str(getattr(rule, "break_start_time", "") or ""),
        "breakEndTime": str(getattr(rule, "break_end_time", "") or ""),
        "breakMinutes": int(getattr(rule, "break_minutes", 0) or 0),
        "computedHours": float(getattr(rule, "computed_hours", 0.0) or 0.0),
    }


def serialize_calendar_exception(exception) -> dict[str, object]:
    """Both the Exceptions table row and the Exception Inspector read this
    same projection -- the Inspector just uses more of its fields (working
    time, description) than the table columns do."""
    exception_date = str(getattr(exception, "exception_date", "") or "")
    exception_type = str(getattr(exception, "exception_type", "") or "")
    impact_type = str(getattr(exception, "impact_type", "") or "")
    approval_status = str(getattr(exception, "approval_status", "") or "")
    return {
        "id": str(getattr(exception, "id", "") or ""),
        "exceptionDate": exception_date,
        "dateLabel": _format_date_label(exception_date),
        "exceptionType": exception_type,
        "typeLabel": _title_case_label(exception_type),
        "name": str(getattr(exception, "name", "") or ""),
        "impactType": impact_type,
        "impactLabel": _title_case_label(impact_type),
        "impactTone": _IMPACT_STATUS_CHIP_TONES.get(impact_type, "neutral"),
        "approvalStatus": approval_status,
        "statusLabel": _title_case_label(approval_status),
        "statusTone": _APPROVAL_STATUS_CHIP_TONES.get(approval_status, "neutral"),
        "description": str(getattr(exception, "description", "") or ""),
        "startTimeLabel": _format_hhmm(getattr(exception, "start_time", "")),
        "endTimeLabel": _format_hhmm(getattr(exception, "end_time", "")),
        "hoursOverride": float(getattr(exception, "hours_override", 0.0) or 0.0),
    }


def serialize_recurring_event(event) -> dict[str, object]:
    """Both the Recurring table row and the Recurring Event Inspector read
    this same projection. `recurrenceLabel` is generated fresh from the
    actual RRULE every time (see recurrence_text.humanize_rrule) -- it is
    never stored or maintained as independent state, so it can never drift
    from what the rule actually does."""
    event_type = str(getattr(event, "event_type", "") or "")
    impact_type = str(getattr(event, "impact_type", "") or "")
    recurrence_rule = str(getattr(event, "recurrence_rule", "") or "")
    effective_from = str(getattr(event, "effective_from", "") or "")
    effective_to = str(getattr(event, "effective_to", "") or "")
    is_active = bool(getattr(event, "is_active", False))
    try:
        parsed_from = _date.fromisoformat(effective_from) if effective_from else None
    except ValueError:
        parsed_from = None
    return {
        "id": str(getattr(event, "id", "") or ""),
        "title": str(getattr(event, "title", "") or ""),
        "eventType": event_type,
        "typeLabel": _title_case_label(event_type),
        "recurrenceRule": recurrence_rule,
        "recurrenceLabel": humanize_rrule(recurrence_rule, effective_from=parsed_from) if recurrence_rule else "",
        "impactType": impact_type,
        "impactLabel": _title_case_label(impact_type),
        "impactTone": _IMPACT_STATUS_CHIP_TONES.get(impact_type, "neutral"),
        "isActive": is_active,
        "statusLabel": "Active" if is_active else "Inactive",
        "statusTone": "success" if is_active else "neutral",
        "startTimeLabel": _format_hhmm(getattr(event, "start_time", "")),
        "endTimeLabel": _format_hhmm(getattr(event, "end_time", "")),
        "effectiveFrom": effective_from,
        "effectiveFromLabel": _format_date_label(effective_from),
        "effectiveTo": effective_to,
        "effectiveToLabel": _format_date_label(effective_to),
        "capacityImpactPercent": float(getattr(event, "capacity_impact_percent", 0.0) or 0.0),
    }


__all__ = [
    "serialize_assignment_groups",
    "serialize_calendar_assignment",
    "serialize_calendar_day_view",
    "serialize_calendar_exception",
    "serialize_recurring_event",
    "serialize_working_rule",
]
