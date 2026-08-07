from __future__ import annotations

from datetime import date, datetime, time, timezone

from src.core.platform.domain.master_data.employee import EmploymentType
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.time_management.calendar.enterprise_calendar import (
    CalendarExceptionORM,
    CalendarRecurringEventORM,
    CalendarWorkingRuleORM,
    DepartmentCalendarAssignmentORM,
    EmployeeCalendarAssignmentORM,
    PlatformCalendarORM,
    ShiftPatternDayORM,
    ShiftPatternORM,
    SiteCalendarAssignmentORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM


def _seed_calendar_scope_rows(services) -> dict[str, str]:
    session = services["session"]
    org_svc = services["organization_service"]
    cur_org = org_svc.get_active_organization()
    oth_org = org_svc.create_organization(
        organization_code="OPS", display_name="Operations Hub",
        timezone_name="UTC", base_currency="USD", is_active=False,
    )
    assert cur_org is not None and oth_org is not None
    ct = getattr(cur_org, "tenant_id", None)
    ot = getattr(oth_org, "tenant_id", None) or ct
    now = datetime.now(timezone.utc)
    today = date.today()

    cur_site = SiteORM(id="site-current", tenant_id=ct, organization_id=cur_org.id,
        site_code="SITE-CUR", name="Current Site", is_active=True,
        created_at=now, updated_at=now, version=1)
    oth_site = SiteORM(id="site-other", tenant_id=ot, organization_id=oth_org.id,
        site_code="SITE-OTH", name="Other Site", is_active=True,
        created_at=now, updated_at=now, version=1)
    cur_dept = DepartmentORM(id="department-current", tenant_id=ct, organization_id=cur_org.id,
        department_code="DEPT-CUR", name="Current Department", is_active=True,
        created_at=now, updated_at=now, version=1)
    oth_dept = DepartmentORM(id="department-other", tenant_id=ot, organization_id=oth_org.id,
        department_code="DEPT-OTH", name="Other Department", is_active=True,
        created_at=now, updated_at=now, version=1)
    cur_emp = EmployeeORM(id="employee-current", tenant_id=ct, organization_id=cur_org.id,
        employee_code="EMP-CUR", full_name="Current Employee",
        employment_type=EmploymentType.FULL_TIME, is_active=True, version=1)
    oth_emp = EmployeeORM(id="employee-other", tenant_id=ot, organization_id=oth_org.id,
        employee_code="EMP-OTH", full_name="Other Employee",
        employment_type=EmploymentType.FULL_TIME, is_active=True, version=1)
    cur_cal = PlatformCalendarORM(id="calendar-current", tenant_id=ct,
        organization_id=cur_org.id, code="CAL-CUR", name="Current Calendar",
        calendar_type="SITE", timezone="UTC", is_default=False, is_active=True,
        priority=0, version=1, created_at=now, updated_at=now)
    oth_cal = PlatformCalendarORM(id="calendar-other", tenant_id=ot,
        organization_id=oth_org.id, code="CAL-OTH", name="Other Calendar",
        calendar_type="SITE", timezone="UTC", is_default=False, is_active=True,
        priority=0, version=1, created_at=now, updated_at=now)
    cur_rule = CalendarWorkingRuleORM(id="rule-current", calendar_id=cur_cal.id,
        weekday=0, is_working_day=True, start_time=time(8, 0), end_time=time(17, 0),
        break_minutes=60, priority=1)
    oth_rule = CalendarWorkingRuleORM(id="rule-other", calendar_id=oth_cal.id,
        weekday=0, is_working_day=True, start_time=time(8, 0), end_time=time(17, 0),
        break_minutes=60, priority=1)
    cur_exc = CalendarExceptionORM(id="exception-current", calendar_id=cur_cal.id,
        exception_date=today, exception_type="HOLIDAY", name="Current Holiday",
        impact_type="NON_WORKING", priority=1, approval_status="APPROVED",
        created_at=now, updated_at=now)
    oth_exc = CalendarExceptionORM(id="exception-other", calendar_id=oth_cal.id,
        exception_date=today, exception_type="HOLIDAY", name="Other Holiday",
        impact_type="NON_WORKING", priority=1, approval_status="APPROVED",
        created_at=now, updated_at=now)
    cur_evt = CalendarRecurringEventORM(id="event-current", calendar_id=cur_cal.id,
        title="Current Recurring", event_type="SHIFT",
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO", start_time=time(8, 0),
        end_time=time(16, 0), impact_type="NON_WORKING", effective_from=today,
        is_active=True, priority=1)
    oth_evt = CalendarRecurringEventORM(id="event-other", calendar_id=oth_cal.id,
        title="Other Recurring", event_type="SHIFT",
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO", start_time=time(8, 0),
        end_time=time(16, 0), impact_type="NON_WORKING", effective_from=today,
        is_active=True, priority=1)
    cur_shift = ShiftPatternORM(id="shift-current", tenant_id=ct,
        organization_id=cur_org.id, code="SHIFT-CUR", name="Current Shift",
        pattern_type="FIXED", timezone="UTC", is_active=True)
    oth_shift = ShiftPatternORM(id="shift-other", tenant_id=ot,
        organization_id=oth_org.id, code="SHIFT-OTH", name="Other Shift",
        pattern_type="FIXED", timezone="UTC", is_active=True)
    cur_day = ShiftPatternDayORM(id="day-current", shift_pattern_id=cur_shift.id,
        day_offset=0, is_working_day=True, start_time=time(8, 0),
        end_time=time(16, 0), break_minutes=30, hours=7.5)
    oth_day = ShiftPatternDayORM(id="day-other", shift_pattern_id=oth_shift.id,
        day_offset=0, is_working_day=True, start_time=time(8, 0),
        end_time=time(16, 0), break_minutes=30, hours=7.5)
    cur_site_asgn = SiteCalendarAssignmentORM(id="site-assignment-current",
        site_id=cur_site.id, calendar_id=cur_cal.id, is_default=True, priority=1)
    oth_site_asgn = SiteCalendarAssignmentORM(id="site-assignment-other",
        site_id=oth_site.id, calendar_id=oth_cal.id, is_default=True, priority=1)
    cur_dept_asgn = DepartmentCalendarAssignmentORM(id="department-assignment-current",
        department_id=cur_dept.id, calendar_id=cur_cal.id, is_default=True, priority=1)
    oth_dept_asgn = DepartmentCalendarAssignmentORM(id="department-assignment-other",
        department_id=oth_dept.id, calendar_id=oth_cal.id, is_default=True, priority=1)
    cur_emp_asgn = EmployeeCalendarAssignmentORM(id="employee-assignment-current",
        employee_id=cur_emp.id, calendar_id=cur_cal.id, is_default=True, priority=1)
    oth_emp_asgn = EmployeeCalendarAssignmentORM(id="employee-assignment-other",
        employee_id=oth_emp.id, calendar_id=oth_cal.id, is_default=True, priority=1)

    session.add_all([cur_site, oth_site, cur_dept, oth_dept, cur_emp, oth_emp,
                     cur_cal, oth_cal, cur_shift, oth_shift])
    session.flush()
    session.add_all([cur_rule, oth_rule, cur_exc, oth_exc, cur_evt, oth_evt,
                     cur_day, oth_day, cur_site_asgn, oth_site_asgn,
                     cur_dept_asgn, oth_dept_asgn, cur_emp_asgn, oth_emp_asgn])
    session.flush()

    return {
        "current_org_id": cur_org.id,
        "other_org_id": oth_org.id,
        "site_other": oth_site.id,
        "department_other": oth_dept.id,
        "employee_other": oth_emp.id,
        "calendar_current": cur_cal.id,
        "calendar_other": oth_cal.id,
        "rule_current": cur_rule.id,
        "rule_other": oth_rule.id,
        "exception_current": cur_exc.id,
        "exception_other": oth_exc.id,
        "event_other": oth_evt.id,
        "shift_current": cur_shift.id,
        "shift_other": oth_shift.id,
        "day_current": cur_day.id,
        "day_other": oth_day.id,
        "site_assignment_other": oth_site_asgn.id,
        "department_assignment_other": oth_dept_asgn.id,
        "employee_assignment_other": oth_emp_asgn.id,
    }


def test_calendar_repositories_scope_cross_organization_access(services) -> None:
    seeded = _seed_calendar_scope_rows(services)
    session = services["session"]

    calendar_repo = services["enterprise_calendar_service"]._calendar_repo
    rule_repo = services["working_rule_service"]._rule_repo
    exception_repo = services["calendar_exception_service"]._exception_repo
    recurring_repo = services["recurring_event_service"]._event_repo
    shift_repo = services["shift_pattern_service"]._pattern_repo
    assignment_repo = services["calendar_assignment_service"]._assignment_repo

    assert calendar_repo.get(seeded["calendar_other"]) is None
    assert rule_repo.get(seeded["rule_other"]) is None
    assert exception_repo.get(seeded["exception_other"]) is None
    assert recurring_repo.get(seeded["event_other"]) is None
    assert shift_repo.get(seeded["shift_other"]) is None
    assert assignment_repo.get_site_assignment(seeded["site_other"]) is None
    assert assignment_repo.get_department_assignment(seeded["department_other"]) is None
    assert assignment_repo.get_employee_assignment(seeded["employee_other"]) is None
    assert calendar_repo.get_by_code(seeded["other_org_id"], "CAL-CUR") is None
    assert calendar_repo.get_global(seeded["other_org_id"]) is None
    assert shift_repo.get_by_code(seeded["other_org_id"], "SHIFT-CUR") is None

    rule_ids = {row.id for row in rule_repo.list_for_calendar(seeded["calendar_current"])}
    shift_day_ids = {row.id for row in shift_repo.list_days(seeded["shift_current"])}
    usage = services["calendar_assignment_service"].list_calendar_assignments(
        seeded["calendar_other"]
    )

    assert calendar_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert shift_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert seeded["rule_current"] in rule_ids
    assert seeded["rule_other"] not in rule_ids
    assert seeded["day_current"] in shift_day_ids
    assert seeded["day_other"] not in shift_day_ids
    assert usage["sites"] == []
    assert usage["departments"] == []
    assert usage["employees"] == []

    rule_repo.delete(seeded["rule_other"])
    exception_repo.delete(seeded["exception_other"])
    recurring_repo.delete(seeded["event_other"])
    shift_repo.delete_day(seeded["day_other"])
    shift_repo.delete(seeded["shift_other"])
    calendar_repo.delete(seeded["calendar_other"])
    assignment_repo.delete_site_assignment(seeded["site_assignment_other"])
    assignment_repo.delete_department_assignment(seeded["department_assignment_other"])
    assignment_repo.delete_employee_assignment(seeded["employee_assignment_other"])
    session.flush()

    assert session.get(CalendarWorkingRuleORM, seeded["rule_other"]) is not None
    assert session.get(CalendarExceptionORM, seeded["exception_other"]) is not None
    assert session.get(CalendarRecurringEventORM, seeded["event_other"]) is not None
    assert session.get(ShiftPatternDayORM, seeded["day_other"]) is not None
    assert session.get(ShiftPatternORM, seeded["shift_other"]) is not None
    assert session.get(PlatformCalendarORM, seeded["calendar_other"]) is not None
    assert session.get(SiteCalendarAssignmentORM, seeded["site_assignment_other"]) is not None
    assert (
        session.get(DepartmentCalendarAssignmentORM, seeded["department_assignment_other"])
        is not None
    )
    assert (
        session.get(EmployeeCalendarAssignmentORM, seeded["employee_assignment_other"])
        is not None
    )
