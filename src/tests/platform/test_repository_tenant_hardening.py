from __future__ import annotations

from datetime import date, datetime, time, timezone

import pytest
from sqlalchemy import select

from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
    ResourceORM,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.employee.domain import EmploymentType
from src.core.platform.infrastructure.persistence.orm.approval import ApprovalRequestORM
from src.core.platform.infrastructure.persistence.orm.audit import AuditLogORM
from src.core.platform.infrastructure.persistence.orm.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.orm.documents import (
    DocumentLinkORM,
    DocumentORM,
    DocumentStructureORM,
)
from src.core.platform.infrastructure.persistence.orm.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.enterprise_calendar import (
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
from src.core.platform.infrastructure.persistence.orm.party import PartyORM
from src.core.platform.infrastructure.persistence.orm.sites import SiteORM
from src.core.platform.infrastructure.persistence.orm.time import (
    TimeEntryORM,
    TimesheetPeriodORM,
)
from src.core.platform.infrastructure.persistence.repositories.approval import (
    SqlAlchemyApprovalRepository,
)
from src.core.platform.infrastructure.persistence.repositories.audit import (
    SqlAlchemyAuditLogRepository,
)
from src.core.platform.infrastructure.persistence.repositories.departments import (
    SqlAlchemyDepartmentRepository,
)
from src.core.platform.infrastructure.persistence.repositories.documents import (
    SqlAlchemyDocumentLinkRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentStructureRepository,
)
from src.core.platform.infrastructure.persistence.repositories.employee import (
    SqlAlchemyEmployeeRepository,
)
from src.core.platform.infrastructure.persistence.repositories.enterprise_calendar import (
    SqlAlchemyCalendarAssignmentRepository,
    SqlAlchemyCalendarExceptionRepository,
    SqlAlchemyCalendarRecurringEventRepository,
    SqlAlchemyCalendarWorkingRuleRepository,
    SqlAlchemyPlatformCalendarRepository,
    SqlAlchemyShiftPatternRepository,
)
from src.core.platform.infrastructure.persistence.repositories.party import (
    SqlAlchemyPartyRepository,
)
from src.core.platform.infrastructure.persistence.repositories.sites import (
    SqlAlchemySiteRepository,
)
from src.core.platform.infrastructure.persistence.repositories.time import (
    SqlAlchemyTimeEntryRepository,
    SqlAlchemyTimesheetPeriodRepository,
)
from src.core.platform.time.domain import TimesheetPeriodStatus


def _seed_platform_scope_rows(services) -> dict[str, str]:
    session = services["session"]
    organization_service = services["organization_service"]
    default_org = organization_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="OPS",
        display_name="Operations Hub",
        timezone_name="UTC",
        base_currency="USD",
        is_active=False,
    )
    assert default_org is not None
    assert other_org is not None

    current_tenant_id = getattr(default_org, "tenant_id", None)
    other_tenant_id = getattr(other_org, "tenant_id", None) or current_tenant_id
    now = datetime.now(timezone.utc)
    earlier = now.replace(hour=max(0, now.hour - 1))
    today = date.today()

    current_site = SiteORM(
        id="site-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        site_code="SITE-CUR",
        name="Current Site",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    other_site = SiteORM(
        id="site-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        site_code="SITE-OTH",
        name="Other Site",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    current_department = DepartmentORM(
        id="department-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        department_code="DEPT-CUR",
        name="Current Department",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    other_department = DepartmentORM(
        id="department-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        department_code="DEPT-OTH",
        name="Other Department",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    current_employee = EmployeeORM(
        id="employee-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        employee_code="EMP-CUR",
        full_name="Current Employee",
        employment_type=EmploymentType.FULL_TIME,
        is_active=True,
        version=1,
    )
    other_employee = EmployeeORM(
        id="employee-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        employee_code="EMP-OTH",
        full_name="Other Employee",
        employment_type=EmploymentType.FULL_TIME,
        is_active=True,
        version=1,
    )
    current_party = PartyORM(
        id="party-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        party_code="PARTY-CUR",
        party_name="Current Party",
        party_type="SUPPLIER",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    other_party = PartyORM(
        id="party-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        party_code="PARTY-OTH",
        party_name="Other Party",
        party_type="SUPPLIER",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    current_structure = DocumentStructureORM(
        id="structure-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        structure_code="STR-CUR",
        name="Current Structure",
        object_scope="GENERAL",
        default_document_type="GENERAL",
        sort_order=0,
        is_active=True,
        version=1,
    )
    other_structure = DocumentStructureORM(
        id="structure-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        structure_code="STR-OTH",
        name="Other Structure",
        object_scope="GENERAL",
        default_document_type="GENERAL",
        sort_order=0,
        is_active=True,
        version=1,
    )
    current_document = DocumentORM(
        id="document-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        document_code="DOC-CUR",
        title="Current Document",
        document_type="GENERAL",
        document_structure_id=current_structure.id,
        storage_kind="FILE_PATH",
        storage_uri="/tmp/current.pdf",
        uploaded_at=now,
        is_current=True,
        is_active=True,
        version=1,
    )
    other_document = DocumentORM(
        id="document-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        document_code="DOC-OTH",
        title="Other Document",
        document_type="GENERAL",
        document_structure_id=other_structure.id,
        storage_kind="FILE_PATH",
        storage_uri="/tmp/other.pdf",
        uploaded_at=now,
        is_current=True,
        is_active=True,
        version=1,
    )
    current_link = DocumentLinkORM(
        id="link-current",
        organization_id=default_org.id,
        document_id=current_document.id,
        module_code="maintenance",
        entity_type="asset",
        entity_id="asset-current",
        link_role="attachment",
    )
    other_link = DocumentLinkORM(
        id="link-other",
        organization_id=other_org.id,
        document_id=other_document.id,
        module_code="maintenance",
        entity_type="asset",
        entity_id="asset-other",
        link_role="attachment",
    )
    current_calendar = PlatformCalendarORM(
        id="calendar-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        code="CAL-CUR",
        name="Current Calendar",
        calendar_type="SITE",
        timezone="UTC",
        is_default=False,
        is_active=True,
        priority=0,
        version=1,
        created_at=now,
        updated_at=now,
    )
    other_calendar = PlatformCalendarORM(
        id="calendar-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        code="CAL-OTH",
        name="Other Calendar",
        calendar_type="SITE",
        timezone="UTC",
        is_default=False,
        is_active=True,
        priority=0,
        version=1,
        created_at=now,
        updated_at=now,
    )
    current_rule = CalendarWorkingRuleORM(
        id="rule-current",
        calendar_id=current_calendar.id,
        weekday=0,
        is_working_day=True,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
        priority=1,
    )
    other_rule = CalendarWorkingRuleORM(
        id="rule-other",
        calendar_id=other_calendar.id,
        weekday=0,
        is_working_day=True,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
        priority=1,
    )
    current_exception = CalendarExceptionORM(
        id="exception-current",
        calendar_id=current_calendar.id,
        exception_date=today,
        exception_type="HOLIDAY",
        name="Current Holiday",
        impact_type="NON_WORKING",
        priority=1,
        approval_status="APPROVED",
        created_at=now,
        updated_at=now,
    )
    other_exception = CalendarExceptionORM(
        id="exception-other",
        calendar_id=other_calendar.id,
        exception_date=today,
        exception_type="HOLIDAY",
        name="Other Holiday",
        impact_type="NON_WORKING",
        priority=1,
        approval_status="APPROVED",
        created_at=now,
        updated_at=now,
    )
    current_event = CalendarRecurringEventORM(
        id="event-current",
        calendar_id=current_calendar.id,
        title="Current Recurring",
        event_type="SHIFT",
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
        start_time=time(8, 0),
        end_time=time(16, 0),
        impact_type="NON_WORKING",
        effective_from=today,
        is_active=True,
        priority=1,
    )
    other_event = CalendarRecurringEventORM(
        id="event-other",
        calendar_id=other_calendar.id,
        title="Other Recurring",
        event_type="SHIFT",
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
        start_time=time(8, 0),
        end_time=time(16, 0),
        impact_type="NON_WORKING",
        effective_from=today,
        is_active=True,
        priority=1,
    )
    current_shift = ShiftPatternORM(
        id="shift-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        code="SHIFT-CUR",
        name="Current Shift",
        pattern_type="FIXED",
        timezone="UTC",
        is_active=True,
    )
    other_shift = ShiftPatternORM(
        id="shift-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        code="SHIFT-OTH",
        name="Other Shift",
        pattern_type="FIXED",
        timezone="UTC",
        is_active=True,
    )
    current_day = ShiftPatternDayORM(
        id="day-current",
        shift_pattern_id=current_shift.id,
        day_offset=0,
        is_working_day=True,
        start_time=time(8, 0),
        end_time=time(16, 0),
        break_minutes=30,
        hours=7.5,
    )
    other_day = ShiftPatternDayORM(
        id="day-other",
        shift_pattern_id=other_shift.id,
        day_offset=0,
        is_working_day=True,
        start_time=time(8, 0),
        end_time=time(16, 0),
        break_minutes=30,
        hours=7.5,
    )
    current_site_assignment = SiteCalendarAssignmentORM(
        id="site-assignment-current",
        site_id=current_site.id,
        calendar_id=current_calendar.id,
        is_default=True,
        priority=1,
    )
    other_site_assignment = SiteCalendarAssignmentORM(
        id="site-assignment-other",
        site_id=other_site.id,
        calendar_id=other_calendar.id,
        is_default=True,
        priority=1,
    )
    current_department_assignment = DepartmentCalendarAssignmentORM(
        id="department-assignment-current",
        department_id=current_department.id,
        calendar_id=current_calendar.id,
        is_default=True,
        priority=1,
    )
    other_department_assignment = DepartmentCalendarAssignmentORM(
        id="department-assignment-other",
        department_id=other_department.id,
        calendar_id=other_calendar.id,
        is_default=True,
        priority=1,
    )
    current_employee_assignment = EmployeeCalendarAssignmentORM(
        id="employee-assignment-current",
        employee_id=current_employee.id,
        calendar_id=current_calendar.id,
        is_default=True,
        priority=1,
    )
    other_employee_assignment = EmployeeCalendarAssignmentORM(
        id="employee-assignment-other",
        employee_id=other_employee.id,
        calendar_id=other_calendar.id,
        is_default=True,
        priority=1,
    )
    current_resource = ResourceORM(
        id="resource-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        name="Current Resource",
        role="Planner",
        hourly_rate=100.0,
        is_active=True,
        capacity_percent=100.0,
        cost_type=CostType.LABOR,
        worker_type=WorkerType.EXTERNAL,
        version=1,
    )
    other_resource = ResourceORM(
        id="resource-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        name="Other Resource",
        role="Planner",
        hourly_rate=100.0,
        is_active=True,
        capacity_percent=100.0,
        cost_type=CostType.LABOR,
        worker_type=WorkerType.EXTERNAL,
        version=1,
    )
    current_time_entry = TimeEntryORM(
        id="time-entry-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        work_allocation_id="allocation-current",
        entry_date=today,
        hours=4.0,
        note="Current work",
        owner_type="work_allocation",
        owner_id="allocation-current",
        created_at=now,
        updated_at=now,
    )
    other_time_entry = TimeEntryORM(
        id="time-entry-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        work_allocation_id="allocation-other",
        entry_date=today,
        hours=5.0,
        note="Other work",
        owner_type="work_allocation",
        owner_id="allocation-other",
        created_at=now,
        updated_at=now,
    )
    current_period = TimesheetPeriodORM(
        id="timesheet-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        resource_id=current_resource.id,
        period_start=today,
        period_end=today,
        status=TimesheetPeriodStatus.SUBMITTED,
        submitted_at=now,
    )
    other_period = TimesheetPeriodORM(
        id="timesheet-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        resource_id=other_resource.id,
        period_start=today,
        period_end=today,
        status=TimesheetPeriodStatus.SUBMITTED,
        submitted_at=earlier,
    )
    current_approval = ApprovalRequestORM(
        id="approval-current",
        tenant_id=current_tenant_id,
        request_type="governance.change",
        entity_type="task",
        entity_id="task-current",
        organization_id=default_org.id,
        payload_json="{}",
        status="PENDING",
        requested_at=now,
    )
    other_approval = ApprovalRequestORM(
        id="approval-other",
        tenant_id=other_tenant_id,
        request_type="governance.change",
        entity_type="task",
        entity_id="task-other",
        organization_id=other_org.id,
        payload_json="{}",
        status="PENDING",
        requested_at=earlier,
    )
    current_audit = AuditLogORM(
        id="audit-current",
        tenant_id=current_tenant_id,
        occurred_at=now,
        action="entity.update",
        entity_type="task",
        entity_id="task-current",
        organization_id=default_org.id,
        details_json="{}",
    )
    other_audit = AuditLogORM(
        id="audit-other",
        tenant_id=other_tenant_id,
        occurred_at=earlier,
        action="entity.update",
        entity_type="task",
        entity_id="task-other",
        organization_id=other_org.id,
        details_json="{}",
    )

    session.add_all(
        [
            current_site,
            other_site,
            current_department,
            other_department,
            current_employee,
            other_employee,
            current_party,
            other_party,
            current_structure,
            other_structure,
            current_document,
            other_document,
            current_link,
            other_link,
            current_calendar,
            other_calendar,
            current_rule,
            other_rule,
            current_exception,
            other_exception,
            current_event,
            other_event,
            current_shift,
            other_shift,
            current_day,
            other_day,
            current_site_assignment,
            other_site_assignment,
            current_department_assignment,
            other_department_assignment,
            current_employee_assignment,
            other_employee_assignment,
            current_resource,
            other_resource,
            current_time_entry,
            other_time_entry,
            current_period,
            other_period,
            current_approval,
            other_approval,
            current_audit,
            other_audit,
        ]
    )
    session.flush()
    return {
        "current_org_id": default_org.id,
        "other_org_id": other_org.id,
        "site_current": current_site.id,
        "site_other": other_site.id,
        "department_current": current_department.id,
        "department_other": other_department.id,
        "employee_current": current_employee.id,
        "employee_other": other_employee.id,
        "party_current": current_party.id,
        "party_other": other_party.id,
        "structure_current": current_structure.id,
        "structure_other": other_structure.id,
        "document_current": current_document.id,
        "document_other": other_document.id,
        "link_current": current_link.id,
        "link_other": other_link.id,
        "calendar_current": current_calendar.id,
        "calendar_other": other_calendar.id,
        "rule_current": current_rule.id,
        "rule_other": other_rule.id,
        "exception_current": current_exception.id,
        "exception_other": other_exception.id,
        "event_current": current_event.id,
        "event_other": other_event.id,
        "shift_current": current_shift.id,
        "shift_other": other_shift.id,
        "day_current": current_day.id,
        "day_other": other_day.id,
        "site_assignment_current": current_site_assignment.id,
        "site_assignment_other": other_site_assignment.id,
        "department_assignment_current": current_department_assignment.id,
        "department_assignment_other": other_department_assignment.id,
        "employee_assignment_current": current_employee_assignment.id,
        "employee_assignment_other": other_employee_assignment.id,
        "time_entry_current": current_time_entry.id,
        "time_entry_other": other_time_entry.id,
        "timesheet_current": current_period.id,
        "timesheet_other": other_period.id,
        "approval_current": current_approval.id,
        "approval_other": other_approval.id,
        "audit_current": current_audit.id,
        "audit_other": other_audit.id,
    }


@pytest.mark.parametrize(
    ("repo_factory", "operation"),
    [
        (SqlAlchemySiteRepository, lambda repo: repo.get("site-1")),
        (SqlAlchemyDepartmentRepository, lambda repo: repo.get("department-1")),
        (SqlAlchemyEmployeeRepository, lambda repo: repo.get("employee-1")),
        (SqlAlchemyPartyRepository, lambda repo: repo.get("party-1")),
        (SqlAlchemyDocumentStructureRepository, lambda repo: repo.get("structure-1")),
        (SqlAlchemyDocumentRepository, lambda repo: repo.get("document-1")),
        (SqlAlchemyDocumentLinkRepository, lambda repo: repo.get("link-1")),
        (SqlAlchemyApprovalRepository, lambda repo: repo.get("approval-1")),
        (SqlAlchemyAuditLogRepository, lambda repo: repo.list_recent(limit=1)),
        (SqlAlchemyTimeEntryRepository, lambda repo: repo.get("time-entry-1")),
        (SqlAlchemyTimesheetPeriodRepository, lambda repo: repo.get("timesheet-1")),
        (SqlAlchemyPlatformCalendarRepository, lambda repo: repo.get("calendar-1")),
        (SqlAlchemyCalendarWorkingRuleRepository, lambda repo: repo.get("rule-1")),
        (SqlAlchemyCalendarExceptionRepository, lambda repo: repo.get("exception-1")),
        (SqlAlchemyCalendarRecurringEventRepository, lambda repo: repo.get("event-1")),
        (SqlAlchemyShiftPatternRepository, lambda repo: repo.get("shift-1")),
        (SqlAlchemyCalendarAssignmentRepository, lambda repo: repo.list_site_assignments("site-1")),
    ],
)
def test_platform_repositories_require_tenant_context_service(
    session, repo_factory, operation
) -> None:
    repo = repo_factory(session)
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        operation(repo)


def test_platform_root_repositories_hide_cross_organization_rows(services) -> None:
    seeded = _seed_platform_scope_rows(services)

    site_repo = services["site_service"]._site_repo
    department_repo = services["department_service"]._department_repo
    employee_repo = services["employee_service"]._employee_repo
    party_repo = services["party_service"]._party_repo
    structure_repo = services["document_service"]._structure_repo
    document_repo = services["document_service"]._document_repo
    link_repo = services["document_service"]._link_repo

    assert site_repo.get(seeded["site_other"]) is None
    assert department_repo.get(seeded["department_other"]) is None
    assert employee_repo.get(seeded["employee_other"]) is None
    assert party_repo.get(seeded["party_other"]) is None
    assert structure_repo.get(seeded["structure_other"]) is None
    assert document_repo.get(seeded["document_other"]) is None
    assert link_repo.get(seeded["link_other"]) is None

    site_ids = {
        row.id
        for row in site_repo.list_for_organization(
            seeded["current_org_id"], active_only=None
        )
    }
    document_ids = {
        row.id
        for row in document_repo.list_for_organization(
            seeded["current_org_id"], active_only=None
        )
    }
    link_ids = {
        row.id
        for row in link_repo.list_for_entity(
            seeded["current_org_id"],
            "maintenance",
            "asset",
            "asset-current",
        )
    }

    assert seeded["site_current"] in site_ids
    assert seeded["site_other"] not in site_ids
    assert seeded["document_current"] in document_ids
    assert seeded["document_other"] not in document_ids
    assert seeded["link_current"] in link_ids
    assert seeded["link_other"] not in link_ids

    link_repo.delete(seeded["link_other"])
    services["session"].flush()
    assert services["session"].get(DocumentLinkORM, seeded["link_other"]) is not None


def test_calendar_repositories_scope_cross_organization_access(services) -> None:
    seeded = _seed_platform_scope_rows(services)
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

    rule_ids = {row.id for row in rule_repo.list_for_calendar(seeded["calendar_current"])}
    shift_day_ids = {row.id for row in shift_repo.list_days(seeded["shift_current"])}
    usage = services["calendar_assignment_service"].list_calendar_assignments(
        seeded["calendar_other"]
    )

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
        session.get(
            DepartmentCalendarAssignmentORM, seeded["department_assignment_other"]
        )
        is not None
    )
    assert (
        session.get(
            EmployeeCalendarAssignmentORM, seeded["employee_assignment_other"]
        )
        is not None
    )


def test_time_and_governance_repositories_scope_cross_organization_data(
    services,
) -> None:
    seeded = _seed_platform_scope_rows(services)
    session = services["session"]

    approval_repo = services["approval_service"]._approval_repo
    audit_repo = services["audit_service"]._audit_repo
    time_entry_repo = services["time_service"]._time_entry_repo
    timesheet_period_repo = services["time_service"]._timesheet_period_repo

    assert approval_repo.get(seeded["approval_other"]) is None
    assert time_entry_repo.get(seeded["time_entry_other"]) is None
    assert timesheet_period_repo.get(seeded["timesheet_other"]) is None

    approval_ids = {row.id for row in approval_repo.list_by_status(limit=200)}
    audit_ids = {row.id for row in audit_repo.list_recent(limit=200)}
    time_entry_ids = {
        row.id
        for row in time_entry_repo.list_for_organization(seeded["current_org_id"])
    }
    review_ids = {
        row.id for row in timesheet_period_repo.list_review_candidates(limit=200)
    }

    assert seeded["approval_current"] in approval_ids
    assert seeded["approval_other"] not in approval_ids
    assert seeded["audit_current"] in audit_ids
    assert seeded["audit_other"] not in audit_ids
    assert seeded["time_entry_current"] in time_entry_ids
    assert seeded["time_entry_other"] not in time_entry_ids
    assert seeded["timesheet_current"] in review_ids
    assert seeded["timesheet_other"] not in review_ids
    assert (
        timesheet_period_repo.list_review_candidates(
            organization_id=seeded["other_org_id"],
            limit=200,
        )
        == []
    )

    time_entry_repo.delete(seeded["time_entry_other"])
    time_entry_repo.delete_by_work_allocation("allocation-other")
    session.flush()
    assert session.get(TimeEntryORM, seeded["time_entry_other"]) is not None
