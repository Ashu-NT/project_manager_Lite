from __future__ import annotations

from src.ui_qml.platform.presenters.common.calendar_summary_support import (
    canonical_source_label,
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
    # The one assignment actually in effect today -- date-filtered and
    # priority-ordered the same way the resolver itself picks a winner,
    # never a raw "first row" from an unfiltered list (a future-dated or
    # expired assignment could otherwise sort first and display wrong).
    assignment_result = None
    if normalized_type == "site":
        assignment_result = controller._enterprise_calendar_api.get_current_site_calendar_assignment(
            normalized_id
        )
        site_id = normalized_id
    elif normalized_type == "department":
        assignment_result = (
            controller._enterprise_calendar_api.get_current_department_calendar_assignment(
                normalized_id
            )
        )
        department_id = normalized_id
    elif normalized_type == "employee":
        assignment_result = (
            controller._enterprise_calendar_api.get_current_employee_calendar_assignment(
                normalized_id
            )
        )
    else:
        return empty_calendar_assignment_context()

    selected_assignment = (
        assignment_result.data
        if assignment_result is not None and getattr(assignment_result, "ok", False)
        else None
    )
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


def _empty_calendar_summary() -> dict[str, object]:
    return {
        "hasCalendar": False,
        "calendarId": "",
        "calendarName": "",
        "source": "",
        "hasOverride": False,
        "workingWeekLabel": "No working days configured",
        "timeZone": "",
        "holidaySetLabel": "No holidays configured",
    }


def _effective_calendar_summary(
    controller,
    *,
    own_prefix: str,
    site_id: str = "",
    department_id: str = "",
    employee_id: str = "",
) -> dict[str, object]:
    """The one implementation every Site/Department/Employee calendar
    summary calls -- never reimplement the Employee/Department/Site/
    Organization fallback independently per entity. Delegates identity
    resolution (which calendar, and the source chain that produced it) to
    PlatformCalendarResolver via resolve_effective_calendar(); only the
    display-ready working-week/holiday labels are fetched locally, for
    whichever single calendar the resolver names as the winner."""
    if controller._enterprise_calendar_api is None:
        return _empty_calendar_summary()

    from src.core.platform.api.desktop.time_management.calendar.models.enterprise_calendar import (
        ResolveEffectiveCalendarCommand,
    )

    result = controller._enterprise_calendar_api.resolve_effective_calendar(
        ResolveEffectiveCalendarCommand(
            site_id=site_id,
            department_id=department_id,
            employee_id=employee_id,
        )
    )
    if not getattr(result, "ok", False) or result.data is None or not result.data.has_calendar:
        return _empty_calendar_summary()

    resolution = result.data
    working_rules = result_sequence(
        controller._enterprise_calendar_api.list_working_rules(resolution.calendar_id)
    )
    working_weekdays = tuple(
        sorted({int(rule.weekday) for rule in working_rules if getattr(rule, "is_working_day", False)})
    )
    exceptions = result_sequence(
        controller._enterprise_calendar_api.list_exceptions(resolution.calendar_id)
    )
    holiday_count = sum(
        1 for exc in exceptions if str(getattr(exc, "exception_type", "")).upper() == "HOLIDAY"
    )
    source_chain = list(resolution.source_chain or [])
    winning_label = source_chain[-1] if source_chain else ""
    winning_prefix = winning_label.split("-", 1)[0] if winning_label else ""
    return {
        "hasCalendar": True,
        "calendarId": resolution.calendar_id,
        "calendarName": resolution.calendar_name,
        "source": canonical_source_label(winning_label, own_prefix=own_prefix),
        # A clean boolean for UI conditional logic -- never string-match the
        # display text in `source` (e.g. checking for the word "override")
        # the way the old per-entity wording used to force callers to.
        "hasOverride": winning_prefix == own_prefix,
        "workingWeekLabel": working_week_label(working_weekdays),
        "timeZone": resolution.timezone,
        "holidaySetLabel": holiday_set_label("", holiday_count),
    }


def site_calendar_summary(
    controller, site_id: str, organization_id: str
) -> dict[str, object]:
    """The Site's effective calendar: its own direct assignment ("Site
    override") when one exists, otherwise the Organization's default
    ("Inherited from Organization") -- resolved through the one canonical
    resolver, never independently reimplemented here. `organization_id` is
    accepted for call-site compatibility but is not needed: the resolver's
    own GLOBAL-level lookup is already tenant/organization-scoped."""
    normalized_site_id = str(site_id or "").strip()
    if not normalized_site_id:
        return _empty_calendar_summary()
    return _effective_calendar_summary(controller, own_prefix="SITE", site_id=normalized_site_id)


def department_calendar_summary(
    controller, department_id: str, organization_id: str, site_id: str = ""
) -> dict[str, object]:
    """The Department's effective calendar, resolved through the real
    chain: a direct Department override, else -- only when the Department
    belongs to a Site -- that Site's own assignment, else the
    Organization's default directly. `source` reports which level actually
    resolved it via the resolver's own source chain, never guessed from
    whether a Department-level assignment merely exists."""
    normalized_department_id = str(department_id or "").strip()
    if not normalized_department_id:
        return _empty_calendar_summary()
    return _effective_calendar_summary(
        controller,
        own_prefix="DEPT",
        site_id=str(site_id or "").strip(),
        department_id=normalized_department_id,
    )


def employee_calendar_summary(
    controller,
    employee_id: str,
    organization_id: str,
    department_id: str = "",
    site_id: str = "",
) -> dict[str, object]:
    """The Employee's effective calendar, resolved through the real chain:
    a direct Employee override, else Department, else Site, else the
    Organization's default -- via the one canonical resolver. `source`
    reports which level actually resolved it rather than guessing from
    whether an Employee-level assignment merely exists."""
    normalized_employee_id = str(employee_id or "").strip()
    if not normalized_employee_id:
        return _empty_calendar_summary()
    return _effective_calendar_summary(
        controller,
        own_prefix="EMP",
        site_id=str(site_id or "").strip(),
        department_id=str(department_id or "").strip(),
        employee_id=normalized_employee_id,
    )


__all__ = [
    "calendar_assignment_context",
    "calendar_detail_context",
    "calendar_source_chain",
    "department_calendar_summary",
    "employee_calendar_summary",
    "empty_calendar_assignment_context",
    "empty_calendar_detail_context",
    "result_sequence",
    "site_calendar_summary",
]
