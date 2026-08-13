from __future__ import annotations

from .admin_calendar_serializers import (
    serialize_assignment_groups,
    serialize_calendar_assignment,
    serialize_calendar_exception,
    serialize_recurring_event,
    serialize_working_rule,
)
from .admin_helpers import empty_calendar_assignment_context, empty_calendar_detail_context


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


__all__ = [
    "calendar_assignment_context",
    "calendar_detail_context",
    "calendar_source_chain",
    "result_sequence",
]
