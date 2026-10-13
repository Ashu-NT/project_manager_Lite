from __future__ import annotations

from src.core.shared.time.business_date import business_today
from src.ui_qml.platform.presenters.common.calendar_summary_support import (
    canonical_source_label,
    holiday_set_label,
    working_week_label,
)

from .serializers import (
    serialize_assignment_groups,
    serialize_calendar_assignment,
    serialize_calendar_day_view,
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
    if controller._platform_calendar_api is None:
        return []
    result = controller._platform_calendar_api.get_source_chain(
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


def _build_assignment_name_lookup(controller) -> dict[str, dict[str, str]]:
    """Resolves Site/Department/Employee display names for Calendar's own
    Assignments tab -- a same-module (Platform-owned) lookup, fetched as ONE
    unbounded list per entity type (the same bounded-organization assumption
    `list_calendars()`/`list_sites()`/etc. already make elsewhere), not one
    query per assignment row. Deliberately does NOT attempt to resolve PM
    Project/Resource names -- Platform has no approved cross-module contract
    for that (see serialize_assignment_groups)."""
    lookup: dict[str, dict[str, str]] = {"sites": {}, "departments": {}, "employees": {}}

    site_api = getattr(controller, "_site_api", None)
    if site_api is not None:
        result = site_api.list_sites()
        if getattr(result, "ok", False) and result.data is not None:
            lookup["sites"] = {s.id: s.name for s in result.data}

    department_api = getattr(controller, "_department_api", None)
    if department_api is not None:
        result = department_api.list_departments()
        if getattr(result, "ok", False) and result.data is not None:
            lookup["departments"] = {d.id: d.name for d in result.data}

    employee_api = getattr(controller, "_employee_api", None)
    if employee_api is not None:
        result = employee_api.list_employees()
        if getattr(result, "ok", False) and result.data is not None:
            lookup["employees"] = {e.id: e.full_name for e in result.data}

    return lookup


def calendar_detail_context(controller, calendar_id: str) -> dict[str, object]:
    if controller._platform_calendar_api is None or not str(calendar_id or "").strip():
        return empty_calendar_detail_context()

    calendar_id = str(calendar_id).strip()
    rules_result = controller._platform_calendar_api.list_working_rules(calendar_id)
    exceptions_result = controller._platform_calendar_api.list_exceptions(calendar_id)
    recurring_result = controller._platform_calendar_api.list_recurring_events(
        calendar_id,
        active_only=False,
    )
    assignments_result = controller._platform_calendar_api.list_calendar_assignments(
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
            else {},
            name_lookup=_build_assignment_name_lookup(controller),
        ),
    }


def calendar_overview_context(controller, calendar_id: str) -> dict[str, object]:
    """Everything Calendar Detail's Overview tab needs in one payload:
    Operational Rules summary (exceptions/recurring/shift-pattern counts),
    Usage summary (organization-default + assignment counts), Upcoming
    Exceptions (future-dated only), and Recent Activity -- built on the same
    workingRules/exceptions/recurringEvents/assignments calendar_detail_context
    already fetches, never a second independent fetch of the same data."""
    detail = calendar_detail_context(controller, calendar_id)
    if controller._platform_calendar_api is None or not str(calendar_id or "").strip():
        return {
            **detail,
            "usage": {"isOrganizationDefault": False, "sites": 0, "departments": 0, "employees": 0, "projects": 0, "resources": 0},
            "upcomingExceptions": [],
            "shiftPatternLabel": "",
            "recentActivity": [],
        }

    calendar_id = str(calendar_id).strip()
    assignments = detail["assignments"]
    calendar_result = controller._platform_calendar_api.get_calendar(calendar_id)
    calendar_dto = calendar_result.data if getattr(calendar_result, "ok", False) else None

    # Working rules don't carry a shift-pattern reference in the current read
    # model (see serialize_working_rule), so this reports whether the
    # organization has ANY active shift pattern configured at all, named
    # generically, rather than guessing which one applies to this calendar.
    shift_pattern_label = ""
    shift_patterns_result = controller._platform_calendar_api.list_shift_patterns(active_only=True)
    if getattr(shift_patterns_result, "ok", False) and shift_patterns_result.data:
        first_pattern = shift_patterns_result.data[0]
        shift_pattern_label = str(getattr(first_pattern, "name", "") or "")

    # "Upcoming" is relative to this calendar's own configured business
    # timezone, not the server's local date -- see
    # PlatformCalendarResolver.business_today for the same rule applied to
    # resolution.
    timezone_name = calendar_dto.timezone if calendar_dto is not None else None
    today = business_today(timezone_name).isoformat()
    upcoming_exceptions = sorted(
        (exc for exc in detail["exceptions"] if exc["exceptionDate"] >= today),
        key=lambda exc: exc["exceptionDate"],
    )[:5]

    org_id = str(calendar_dto.organization_id) if calendar_dto is not None else ""
    recent_activity = (
        controller._calendar_controller.calendarActivity(calendar_id, org_id)
        if org_id
        else []
    )

    return {
        **detail,
        "calendar": {
            "name": calendar_dto.name if calendar_dto is not None else "",
            "code": calendar_dto.code if calendar_dto is not None else "",
            "description": calendar_dto.description if calendar_dto is not None else "",
            "timeZone": calendar_dto.timezone if calendar_dto is not None else "",
            "calendarType": calendar_dto.calendar_type if calendar_dto is not None else "",
            "isDefault": bool(calendar_dto.is_default) if calendar_dto is not None else False,
            "isActive": bool(calendar_dto.is_active) if calendar_dto is not None else True,
            "effectiveFrom": calendar_dto.effective_from if calendar_dto is not None else "",
            "effectiveTo": calendar_dto.effective_to if calendar_dto is not None else "",
        },
        "usage": {
            "isOrganizationDefault": bool(calendar_dto.is_default) if calendar_dto is not None else False,
            "sites": len(assignments["sites"]),
            "departments": len(assignments["departments"]),
            "employees": len(assignments["employees"]),
            "projects": len(assignments["projects"]),
            "resources": len(assignments["resources"]),
        },
        "upcomingExceptions": upcoming_exceptions,
        "shiftPatternLabel": shift_pattern_label,
        "recentActivity": recent_activity,
    }


def calendar_assignment_context(
    controller,
    entity_type: str,
    entity_id: str,
    site_id: str = "",
    department_id: str = "",
) -> dict[str, object]:
    if controller._platform_calendar_api is None or not str(entity_id or "").strip():
        return empty_calendar_assignment_context()

    normalized_type = str(entity_type or "").strip().lower()
    normalized_id = str(entity_id or "").strip()
    # The one assignment actually in effect today -- date-filtered and
    # priority-ordered the same way the resolver itself picks a winner,
    # never a raw "first row" from an unfiltered list (a future-dated or
    # expired assignment could otherwise sort first and display wrong).
    assignment_result = None
    if normalized_type == "site":
        assignment_result = controller._platform_calendar_api.get_current_site_calendar_assignment(
            normalized_id
        )
        site_id = normalized_id
    elif normalized_type == "department":
        assignment_result = (
            controller._platform_calendar_api.get_current_department_calendar_assignment(
                normalized_id
            )
        )
        department_id = normalized_id
    elif normalized_type == "employee":
        assignment_result = (
            controller._platform_calendar_api.get_current_employee_calendar_assignment(
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
    if controller._platform_calendar_api is None:
        return _empty_calendar_summary()

    from src.core.platform.api.desktop.time_management.calendar.models.platform_calendar import (
        ResolveEffectiveCalendarCommand,
    )

    result = controller._platform_calendar_api.resolve_effective_calendar(
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
        controller._platform_calendar_api.list_working_rules(resolution.calendar_id)
    )
    working_weekdays = tuple(
        sorted({int(rule.weekday) for rule in working_rules if getattr(rule, "is_working_day", False)})
    )
    exceptions = result_sequence(
        controller._platform_calendar_api.list_exceptions(resolution.calendar_id)
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


def _calendar_timezone(controller, calendar_id: str) -> str | None:
    if controller._platform_calendar_api is None:
        return None
    result = controller._platform_calendar_api.get_calendar(calendar_id)
    if not getattr(result, "ok", False) or result.data is None:
        return None
    return result.data.timezone


def calendar_business_today(controller, calendar_id: str) -> str:
    """"Today" in this calendar's own configured business timezone -- the
    Month view's initial month and "Today" button must use this, never a
    QML `new Date()`, which only knows the client machine's local clock."""
    timezone_name = _calendar_timezone(controller, str(calendar_id or "").strip())
    return business_today(timezone_name).isoformat()


def empty_calendar_month_context() -> dict[str, object]:
    return {"ok": True, "days": [], "errorMessage": ""}


def calendar_month_context(
    controller, calendar_id: str, start_date: str, end_date: str
) -> dict[str, object]:
    """One bounded range resolution per visible month grid (including
    leading/trailing adjacent-month dates the grid itself decided to show) --
    never one call per day. `start_date`/`end_date` are whatever the QML
    MonthGrid actually renders; this does not recompute or second-guess
    that boundary."""
    calendar_id = str(calendar_id or "").strip()
    if controller._platform_calendar_api is None or not calendar_id:
        return empty_calendar_month_context()

    timezone_name = _calendar_timezone(controller, calendar_id)
    today_iso = business_today(timezone_name).isoformat()

    from src.core.platform.api.desktop.time_management.calendar.models.platform_calendar import (
        ResolveCalendarRangeCommand,
    )

    result = controller._platform_calendar_api.resolve_calendar_range(
        ResolveCalendarRangeCommand(start_date=start_date, end_date=end_date)
    )
    if not getattr(result, "ok", False) or result.data is None:
        message = (
            result.error.message
            if result is not None and getattr(result, "error", None) is not None
            else "Unable to load calendar data for this month."
        )
        return {"ok": False, "days": [], "errorMessage": message}

    return {
        "ok": True,
        "errorMessage": "",
        "days": [serialize_calendar_day_view(day, today_iso=today_iso) for day in result.data],
    }


__all__ = [
    "calendar_assignment_context",
    "calendar_business_today",
    "calendar_detail_context",
    "calendar_month_context",
    "calendar_overview_context",
    "calendar_source_chain",
    "department_calendar_summary",
    "employee_calendar_summary",
    "empty_calendar_assignment_context",
    "empty_calendar_detail_context",
    "empty_calendar_month_context",
    "result_sequence",
    "site_calendar_summary",
]
