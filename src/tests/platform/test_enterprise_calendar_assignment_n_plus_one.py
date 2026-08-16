"""P5 -- regression guardrail for the confirmed N+1 in
EnterpriseCalendarDesktopApi._serialize_assignment
(src/core/platform/api/desktop/time_management/calendar/enterprise_calendar.py).

Before the fix, every method that serialized a list of calendar
assignments (list_site/department/employee_calendar_assignments and the
combined list_calendar_assignments) called get_calendar(assignment.calendar_id)
once per returned assignment -- O(N) calendar lookups for N assignments,
even when every assignment referenced the same calendar. The fix batches
all distinct calendar_ids referenced by a list into one lookup
(EnterpriseCalendarService.get_calendars_by_ids -> PlatformCalendarRepository
.list_by_ids) and made _serialize_assignment pure (it now takes the
already-resolved calendar instead of fetching it itself).

These tests pin that behavior so it cannot silently regress back to a
per-assignment get_calendar() loop, and confirm every assignment category
(site/department/employee/project/resource) still serializes identically.
"""
from __future__ import annotations

from sqlalchemy import event

from src.core.platform.api.desktop.time_management.calendar.enterprise_calendar import (
    EnterpriseCalendarDesktopApi,
)


def _build_api(services):
    return EnterpriseCalendarDesktopApi(
        calendar_service=services["enterprise_calendar_service"],
        rule_service=services["working_rule_service"],
        exception_service=services["calendar_exception_service"],
        recurring_event_service=services["recurring_event_service"],
        shift_pattern_service=services["shift_pattern_service"],
        assignment_service=services["calendar_assignment_service"],
        resolver=services["enterprise_calendar_resolver"],
        capacity_calculator=services.get("resource_capacity_calculator"),
    )


def _instrument(calendar_repo):
    """Wrap get()/list_by_ids() on this instance's class with counters.
    Returns (counts dict, restore callback)."""
    counts = {"get": 0, "list_by_ids": 0}
    cls = type(calendar_repo)
    real_get = cls.get
    real_list_by_ids = cls.list_by_ids

    def counting_get(self, *args, **kwargs):
        counts["get"] += 1
        return real_get(self, *args, **kwargs)

    def counting_list_by_ids(self, *args, **kwargs):
        counts["list_by_ids"] += 1
        return real_list_by_ids(self, *args, **kwargs)

    cls.get = counting_get
    cls.list_by_ids = counting_list_by_ids

    def restore():
        cls.get = real_get
        cls.list_by_ids = real_list_by_ids

    return counts, restore


def _count_calendar_selects(engine, fn):
    selects = []

    def _listener(conn, cursor, statement, parameters, context, executemany):
        if "platform_calendars" in statement:
            selects.append(statement)

    event.listen(engine, "before_cursor_execute", _listener)
    try:
        result = fn()
    finally:
        event.remove(engine, "before_cursor_execute", _listener)
    return result, len(selects)


def _make_departments_against_one_shared_calendar(services, n, suffix):
    calendar = services["enterprise_calendar_service"].create_calendar(
        code=f"CAL-{suffix}", name=f"Calendar {suffix}", calendar_type="DEPARTMENT"
    )
    for i in range(n):
        dept = services["department_service"].create_department(
            department_code=f"DEPT-{suffix}-{i}", name=f"Dept {suffix} {i}"
        )
        services["calendar_assignment_service"].assign_department_calendar(dept.id, calendar.id)
    return calendar


def test_list_department_assignments_calendar_lookup_stays_constant(services, session):
    """Regression guardrail for list_department_calendar_assignments
    (same shape covers list_site_/list_employee_calendar_assignments,
    which share the batch-then-serialize code path)."""
    api = _build_api(services)
    calendar_repo = services["enterprise_calendar_service"]._calendar_repo

    def _measure(n, suffix):
        calendar = _make_departments_against_one_shared_calendar(services, n, suffix)
        dept_ids = [
            a.department_id
            for a in services["calendar_assignment_service"].list_calendar_assignments(
                calendar.id
            )["departments"]
        ]
        assert len(dept_ids) == n
        counts, restore = _instrument(calendar_repo)
        try:
            results = [
                api.list_department_calendar_assignments(dept_id) for dept_id in dept_ids
            ]
        finally:
            restore()
        assert all(r.ok for r in results)
        return counts["get"], counts["list_by_ids"]

    get_1, batch_1 = _measure(1, "one")
    get_10, batch_10 = _measure(10, "ten")

    assert get_1 == 0 and get_10 == 0, (
        "list_department_calendar_assignments must never call get_calendar() directly -- "
        f"got {get_1} calls for 1 department, {get_10} for 10"
    )
    assert batch_1 == 1 and batch_10 == 10, (
        "expected exactly one batch lookup PER list_department_calendar_assignments call "
        f"(1 department -> 1 call, 10 departments -> 10 calls), got {batch_1} and {batch_10} -- "
        "each individual call must still cost exactly one batch lookup regardless of how many "
        "assignments that one department has"
    )


def test_list_calendar_assignments_issues_one_calendar_lookup_regardless_of_assignment_count(
    services, session
):
    api = _build_api(services)
    calendar_repo = services["enterprise_calendar_service"]._calendar_repo
    engine = session.get_bind()

    def _measure(n, suffix):
        calendar = _make_departments_against_one_shared_calendar(services, n, suffix)
        counts, restore = _instrument(calendar_repo)
        try:
            result, selects = _count_calendar_selects(
                engine, lambda: api.list_calendar_assignments(calendar.id)
            )
        finally:
            restore()
        assert result.ok is True, result.error
        dto_count = sum(len(v) for v in result.data.values())
        assert dto_count == n
        return counts["get"], selects

    get_1, selects_1 = _measure(1, "one")
    get_10, selects_10 = _measure(10, "ten")
    get_50, selects_50 = _measure(50, "fifty")

    assert (get_1, get_10, get_50) == (1, 1, 1), (
        "list_calendar_assignments must issue exactly one get_calendar() call regardless of "
        f"how many assignments reference that calendar -- got {(get_1, get_10, get_50)} for "
        "1/10/50 assignments (this is the confirmed N+1 the audit flagged)"
    )
    assert selects_1 == selects_10 == selects_50


def test_list_calendar_assignments_serializes_all_five_entity_types_correctly(services):
    """P5.4 -- semantic equivalence: every assignment category still
    produces a DTO with the correct entity_type/entity_id and the shared
    calendar's name/type, exactly as before the batch-fetch rewire."""
    organization = services["organization_service"].get_active_organization()
    calendar_service = services["enterprise_calendar_service"]
    assignment_service = services["calendar_assignment_service"]
    api = _build_api(services)

    calendar = calendar_service.create_calendar(
        code="CAL-ALL5", name="Shared Calendar", calendar_type="GLOBAL"
    )

    site = services["site_service"].create_site(site_code="P5-SITE", name="P5 Site")
    department = services["department_service"].create_department(
        department_code="P5-DEPT", name="P5 Department"
    )
    employee = services["employee_service"].create_employee(
        employee_code="P5-EMP", full_name="P5 Employee", employment_type="FULL_TIME"
    )
    project = services["project_service"].create_project(
        "P5 Project", financial_currency_code=organization.base_currency
    )
    resource = services["resource_service"].create_resource(
        "P5 Resource", hourly_rate=0, currency_code=organization.base_currency
    )

    assignment_service.assign_site_calendar(site.id, calendar.id)
    assignment_service.assign_department_calendar(department.id, calendar.id)
    assignment_service.assign_employee_calendar(employee.id, calendar.id)
    assignment_service.assign_project_calendar(project.id, calendar.id)
    assignment_service.assign_resource_calendar(resource.id, calendar.id)

    result = api.list_calendar_assignments(calendar.id)
    assert result.ok is True, result.error
    usage = result.data

    def _assert_one(category, entity_type, entity_id):
        assert len(usage[category]) == 1
        dto = usage[category][0]
        assert dto.entity_type == entity_type
        assert dto.entity_id == entity_id
        assert dto.calendar_id == calendar.id
        assert dto.calendar_name == "Shared Calendar"
        assert dto.calendar_type == "GLOBAL"

    _assert_one("sites", "site", site.id)
    _assert_one("departments", "department", department.id)
    _assert_one("employees", "employee", employee.id)
    _assert_one("projects", "project", project.id)
    _assert_one("resources", "resource", resource.id)


def test_single_assignment_write_paths_still_return_correct_calendar_fields(services):
    """The 5 assign_*_calendar write methods aren't part of the N+1 (each
    is inherently a single assignment), but they share the now-pure
    _serialize_assignment -- confirm the rewire didn't change their output."""
    calendar_service = services["enterprise_calendar_service"]
    api = _build_api(services)

    calendar = calendar_service.create_calendar(
        code="CAL-WRITE", name="Write Path Calendar", calendar_type="SITE"
    )
    site = services["site_service"].create_site(site_code="P5-WRITE-SITE", name="Write Site")

    from src.core.platform.api.desktop.time_management.calendar.models.enterprise_calendar import (
        SiteCalendarAssignCommand,
    )

    result = api.assign_site_calendar(
        SiteCalendarAssignCommand(
            site_id=site.id,
            calendar_id=calendar.id,
            effective_from="",
            effective_to="",
            is_default=True,
            priority=0,
        )
    )
    assert result.ok is True, result.error
    assert result.data.entity_type == "site"
    assert result.data.entity_id == site.id
    assert result.data.calendar_name == "Write Path Calendar"
    assert result.data.calendar_type == "SITE"
