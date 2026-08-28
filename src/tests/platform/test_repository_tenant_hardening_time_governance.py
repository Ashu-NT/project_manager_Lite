from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
    ResourceORM,
)
from src.core.platform.infrastructure.persistence.orm.approval.approval import ApprovalRequestORM
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import AuditEntryORM
from src.core.platform.infrastructure.persistence.orm.time_management.time.time import (
    TimeEntryORM,
    TimesheetPeriodORM,
)
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


def _seed_time_governance_scope_rows(services) -> dict[str, str]:
    session = services["session"]
    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="OPS",
        display_name="Operations Hub",
        timezone_name="UTC",
        base_currency="USD",
        is_enabled=False,
    )
    assert default_org is not None
    assert other_org is not None

    current_tenant_id = getattr(default_org, "tenant_id", None)
    other_tenant_id = getattr(other_org, "tenant_id", None) or current_tenant_id
    now = datetime.now(timezone.utc)
    earlier = now.replace(hour=max(0, now.hour - 1))
    today = date.today()

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
    current_audit = AuditEntryORM(
        id="audit-current",
        tenant_id=current_tenant_id,
        timestamp=now,
        operation="update",
        entity_type="task",
        entity_id="task-current",
        organization_id=default_org.id,
        module="platform",
        source="api",
        severity="low",
        compliance_tag="none",
        metadata_json="{}",
    )
    other_audit = AuditEntryORM(
        id="audit-other",
        tenant_id=other_tenant_id,
        timestamp=earlier,
        operation="update",
        entity_type="task",
        entity_id="task-other",
        organization_id=other_org.id,
        module="platform",
        source="api",
        severity="low",
        compliance_tag="none",
        metadata_json="{}",
    )

    session.add_all([
        current_resource, other_resource,
        current_time_entry, other_time_entry,
        current_approval, other_approval,
        current_audit, other_audit,
    ])
    session.flush()
    session.add_all([current_period, other_period])
    session.flush()

    return {
        "current_org_id": default_org.id,
        "other_org_id": other_org.id,
        "time_entry_current": current_time_entry.id,
        "time_entry_other": other_time_entry.id,
        "timesheet_current": current_period.id,
        "timesheet_other": other_period.id,
        "approval_current": current_approval.id,
        "approval_other": other_approval.id,
        "audit_current": current_audit.id,
        "audit_other": other_audit.id,
    }


def test_time_and_governance_repositories_scope_cross_organization_data(
    services,
) -> None:
    seeded = _seed_time_governance_scope_rows(services)
    session = services["session"]

    approval_repo = services["approval_service"]._approval_repo
    audit_repo = services["enterprise_audit_service"]._audit_repo
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

    assert approval_repo.list_by_status_for_organization(seeded["other_org_id"], limit=200) == []
    assert audit_repo.list_recent_for_organization(seeded["other_org_id"], limit=200) == []
    assert time_entry_repo.list_for_organization(seeded["other_org_id"]) == []
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
