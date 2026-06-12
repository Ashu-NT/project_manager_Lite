from __future__ import annotations


def serialize_calendar_assignment(assignment) -> dict[str, object]:
    if assignment is None:
        return {}
    return {
        "assignmentId": str(getattr(assignment, "id", "") or ""),
        "entityType": str(getattr(assignment, "entity_type", "") or ""),
        "entityId": str(getattr(assignment, "entity_id", "") or ""),
        "calendarId": str(getattr(assignment, "calendar_id", "") or ""),
        "calendarName": str(getattr(assignment, "calendar_name", "") or ""),
        "calendarType": str(getattr(assignment, "calendar_type", "") or ""),
        "isDefault": bool(getattr(assignment, "is_default", False)),
        "priority": int(getattr(assignment, "priority", 0) or 0),
        "effectiveFrom": str(getattr(assignment, "effective_from", "") or ""),
        "effectiveTo": str(getattr(assignment, "effective_to", "") or ""),
    }


def serialize_assignment_groups(assignments: object) -> dict[str, object]:
    from .admin_helpers import empty_calendar_detail_context
    if not isinstance(assignments, dict):
        return empty_calendar_detail_context()["assignments"]
    return {
        "sites": [
            serialize_calendar_assignment(item) for item in assignments.get("sites", ())
        ],
        "departments": [
            serialize_calendar_assignment(item) for item in assignments.get("departments", ())
        ],
        "employees": [
            serialize_calendar_assignment(item) for item in assignments.get("employees", ())
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
        "breakMinutes": int(getattr(rule, "break_minutes", 0) or 0),
        "computedHours": float(getattr(rule, "computed_hours", 0.0) or 0.0),
    }


def serialize_calendar_exception(exception) -> dict[str, object]:
    return {
        "id": str(getattr(exception, "id", "") or ""),
        "exceptionDate": str(getattr(exception, "exception_date", "") or ""),
        "exceptionType": str(getattr(exception, "exception_type", "") or ""),
        "name": str(getattr(exception, "name", "") or ""),
        "impactType": str(getattr(exception, "impact_type", "") or ""),
        "approvalStatus": str(getattr(exception, "approval_status", "") or ""),
    }


def serialize_recurring_event(event) -> dict[str, object]:
    return {
        "id": str(getattr(event, "id", "") or ""),
        "title": str(getattr(event, "title", "") or ""),
        "eventType": str(getattr(event, "event_type", "") or ""),
        "recurrenceRule": str(getattr(event, "recurrence_rule", "") or ""),
        "impactType": str(getattr(event, "impact_type", "") or ""),
        "isActive": bool(getattr(event, "is_active", False)),
    }


__all__ = [
    "serialize_assignment_groups",
    "serialize_calendar_assignment",
    "serialize_calendar_exception",
    "serialize_recurring_event",
    "serialize_working_rule",
]
