from __future__ import annotations

from src.ui_qml.platform.presenters.common.calendar_summary_support import (
    holiday_set_label,
    working_week_label,
)

from .serializers import (
    serialize_assignment_groups,
    serialize_calendar_assignment,
    serialize_calendar_exception,
    serialize_recurring_event,
    serialize_working_rule,
)


def empty_calendar_detail_context() -> dict[str, object]:
    return {
        "workingRules": [],
        "exceptions": [],
        "recurringEvents": [],
        "assignments": {
            "sites": [],
            "departments": [],
            "employees": [],
            "projects": [],
            "resources": [],
        },
    }


def empty_calendar_assignment_context() -> dict[str, object]:
    return {
        "assignedCalendar": {},
        "sourceChain": [],
    }


def result_sequence(result) -> list[object]:
    if (
        result is None
        or not getattr(result, "ok", False)
        or getattr(result, "data", None) is None
    ):
        return []
    data = result.data
    if isinstance(data, (list, tuple)):
        return list(data)
    return []


def calendar_source_chain(
    controller,
    *,
    normalized_type: str,
    entity_id: str,
    site_id: str,
    department_id: str,
) -> list[str]:
    if controller._enterprise_calendar_api is None:
        return []
    result = controller._enterprise_calendar_api.get_source_chain(
        site_id=entity_id if normalized_type == "site" else str(site_id or ""),
        department_id=entity_id
        if normalized_type == "department"
        else str(department_id or ""),
        employee_id=entity_id if normalized_type == "employee" else "",
    )
    if (
        result is None
        or not getattr(result, "ok", False)
        or getattr(result, "data", None) is None
    ):
        return []
    return [str(item) for item in result.data]


def calendar_detail_context(controller, calendar_id: str) -> dict[str, object]:
    if controller._enterprise_calendar_api is None or not str(calendar_id or "").strip():
        return empty_calendar_detail_context()

    calendar_id = str(calendar_id).strip()
    rules_result = controller._enterprise_calendar_api.list_working_rules(calendar_id)
    exceptions_result = controller._enterprise_calendar_api.list_exceptions(calendar_id)
    recurring_result = controller._enterprise_calendar_api.list_recurring_events(
        calendar_id,
        active_only=False,
    )
    assignments_result = controller._enterprise_calendar_api.list_calendar_assignments(
        calendar_id
    )

    return {
        "workingRules": [
            serialize_working_rule(rule) for rule in result_sequence(rules_result)
        ],
        "exceptions": [
            serialize_calendar_exception(exc) for exc in result_sequence(exceptions_result)
        ],
        "recurringEvents": [
            serialize_recurring_event(event) for event in result_sequence(recurring_result)
        ],
        "assignments": serialize_assignment_groups(
            assignments_result.data
            if getattr(assignments_result, "ok", False)
            and getattr(assignments_result, "data", None) is not None
            else {}
        ),
    }


def calendar_assignment_context(
    controller,
    entity_type: str,
    entity_id: str,
    site_id: str = "",
    department_id: str = "",
) -> dict[str, object]:
    if controller._enterprise_calendar_api is None or not str(entity_id or "").strip():
        return empty_calendar_assignment_context()

    normalized_type = str(entity_type or "").strip().lower()
    normalized_id = str(entity_id or "").strip()
    assignment_result = None
    if normalized_type == "site":
        assignment_result = controller._enterprise_calendar_api.list_site_calendar_assignments(
            normalized_id
        )
        site_id = normalized_id
    elif normalized_type == "department":
        assignment_result = (
            controller._enterprise_calendar_api.list_department_calendar_assignments(
                normalized_id
            )
        )
        department_id = normalized_id
    elif normalized_type == "employee":
        assignment_result = (
            controller._enterprise_calendar_api.list_employee_calendar_assignments(
                normalized_id
            )
        )
    else:
        return empty_calendar_assignment_context()

    assignments = result_sequence(assignment_result)
    selected_assignment = assignments[0] if assignments else None
    source_chain = calendar_source_chain(
        controller,
        normalized_type=normalized_type,
        entity_id=normalized_id,
        site_id=site_id,
        department_id=department_id,
    )
    return {
        "assignedCalendar": serialize_calendar_assignment(selected_assignment),
        "sourceChain": source_chain,
    }


def _empty_site_calendar_summary() -> dict[str, object]:
    return {
        "hasCalendar": False,
        "calendarId": "",
        "calendarName": "",
        "source": "",
        "workingWeekLabel": "No working days configured",
        "timeZone": "",
        "holidaySetLabel": "No holidays configured",
    }


def site_calendar_summary(
    controller, site_id: str, organization_id: str
) -> dict[str, object]:
    """The Site's effective calendar: its own direct assignment when one
    exists ("override"), otherwise the Organization's default GLOBAL
    calendar ("inherited") -- the same fallback
    AdminCalendarAssignmentSection's inheritance chain already resolves,
    pre-computed here into one display-ready summary (name + source +
    working week + holiday count) instead of a raw assignment row, so the
    UI never has to guess or hardcode a generic "Global calendar" fallback
    label."""
    normalized_site_id = str(site_id or "").strip()
    if not normalized_site_id or controller._enterprise_calendar_api is None:
        return _empty_site_calendar_summary()

    assignments = result_sequence(
        controller._enterprise_calendar_api.list_site_calendar_assignments(normalized_site_id)
    )
    if assignments:
        assignment = assignments[0]
        calendar_id = str(getattr(assignment, "calendar_id", "") or "")
        calendar_name = str(getattr(assignment, "calendar_name", "") or "")
        timezone = ""
        calendar_result = controller._enterprise_calendar_api.get_calendar(calendar_id)
        if getattr(calendar_result, "ok", False) and getattr(calendar_result, "data", None) is not None:
            timezone = str(calendar_result.data.timezone or "")
        working_rules = result_sequence(controller._enterprise_calendar_api.list_working_rules(calendar_id))
        working_weekdays = tuple(
            sorted({int(rule.weekday) for rule in working_rules if getattr(rule, "is_working_day", False)})
        )
        exceptions = result_sequence(controller._enterprise_calendar_api.list_exceptions(calendar_id))
        holiday_count = sum(
            1 for exc in exceptions if str(getattr(exc, "exception_type", "")).upper() == "HOLIDAY"
        )
        return {
            "hasCalendar": True,
            "calendarId": calendar_id,
            "calendarName": calendar_name,
            "source": "override",
            "workingWeekLabel": working_week_label(working_weekdays),
            "timeZone": timezone,
            "holidaySetLabel": holiday_set_label("", holiday_count),
        }

    normalized_org_id = str(organization_id or "").strip()
    if not normalized_org_id or controller._runtime_api is None:
        return _empty_site_calendar_summary()
    org_result = controller._runtime_api.get_organization_calendar_summary(normalized_org_id)
    if not getattr(org_result, "ok", False) or org_result.data is None or not org_result.data.has_calendar:
        return _empty_site_calendar_summary()
    data = org_result.data
    return {
        "hasCalendar": True,
        "calendarId": data.calendar_id,
        "calendarName": data.calendar_name,
        "source": "inherited",
        "workingWeekLabel": working_week_label(tuple(data.working_weekdays)),
        "timeZone": data.timezone,
        "holidaySetLabel": holiday_set_label(data.locale, data.holiday_count),
    }


__all__ = [
    "calendar_assignment_context",
    "calendar_detail_context",
    "calendar_source_chain",
    "empty_calendar_assignment_context",
    "empty_calendar_detail_context",
    "result_sequence",
    "site_calendar_summary",
]
