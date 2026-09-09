from __future__ import annotations

from datetime import date

from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceIdentityReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.timesheets.sqlalchemy_workspace_reader import (
    SqlAlchemyTimesheetWorkspaceReader,
)


def _tenant_org(services):
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    organization = services["tenant_context_service"].get_active_organization()
    return tenant_id, organization.id


def _reader(session) -> SqlAlchemyTimesheetWorkspaceReader:
    return SqlAlchemyTimesheetWorkspaceReader(
        session=session,
        resource_identity_reader=SqlAlchemyResourceIdentityReader(session=session),
    )


def _setup_resource_with_open_periods(services, *, month_count: int):
    tenant_id, organization_id = _tenant_org(services)
    project = services["project_service"].create_project(
        "Open Period Parity Project",
        financial_currency_code=services["tenant_context_service"]
        .get_active_organization()
        .base_currency,
    )
    task = services["task_service"].create_task(
        project.id, "Parity task", start_date=date(2026, 1, 1), duration_days=2
    )
    resource = services["resource_service"].create_resource("Parity Resource")
    assignment = services["task_service"].assign_resource(
        task.id, resource.id, allocation_percent=50.0
    )
    for month in range(1, month_count + 1):
        services["task_service"].add_time_entry(
            assignment.id, entry_date=date(2026, month, 4), hours=2
        )
    return resource, tenant_id, organization_id


def test_open_period_count_equals_the_full_list_cardinality_when_unbounded(services, session):
    resource, tenant_id, organization_id = _setup_resource_with_open_periods(
        services, month_count=5
    )
    reader = _reader(session)

    exact_count = reader.count_open_periods(
        resource=_resource_fact(reader, resource, tenant_id, organization_id),
        tenant_id=tenant_id,
        organization_id=organization_id,
    )
    full_list = reader.list_open_periods(
        resource=_resource_fact(reader, resource, tenant_id, organization_id),
        tenant_id=tenant_id,
        organization_id=organization_id,
        limit=100,
    )

    assert exact_count == 5
    assert len(full_list) == exact_count


def test_open_period_count_is_unaffected_by_a_smaller_preview_limit(services, session):
    """The bounded preview may return fewer items; the exact count must
    still reflect the complete matching set, since both share the same
    underlying candidate-resolution logic."""
    resource, tenant_id, organization_id = _setup_resource_with_open_periods(
        services, month_count=5
    )
    reader = _reader(session)
    resource_fact = _resource_fact(reader, resource, tenant_id, organization_id)

    exact_count = reader.count_open_periods(
        resource=resource_fact, tenant_id=tenant_id, organization_id=organization_id
    )
    bounded_preview = reader.list_open_periods(
        resource=resource_fact, tenant_id=tenant_id, organization_id=organization_id, limit=2
    )

    assert exact_count == 5
    assert len(bounded_preview) == 2
    assert len(bounded_preview) < exact_count


def test_open_period_count_and_list_agree_on_zero_when_none_are_open(services, session):
    tenant_id, organization_id = _tenant_org(services)
    resource = services["resource_service"].create_resource("No Entries Resource")
    reader = _reader(session)
    resource_fact = _resource_fact(reader, resource, tenant_id, organization_id)

    assert (
        reader.count_open_periods(
            resource=resource_fact, tenant_id=tenant_id, organization_id=organization_id
        )
        == 0
    )
    assert (
        reader.list_open_periods(
            resource=resource_fact, tenant_id=tenant_id, organization_id=organization_id, limit=50
        )
        == ()
    )


def _resource_fact(reader, resource, tenant_id, organization_id):
    """Both count_open_periods/list_open_periods take a TimesheetResourceFact
    (not a bare resource_id), matching read_history's own signature -- build
    it the same way resolve_mine_resource would, without needing a linked
    user for this parity check."""
    from src.core.modules.project_management.contracts.reads.timesheets import (
        TimesheetResourceFact,
    )

    return TimesheetResourceFact(
        resource_id=resource.id,
        resource_name=resource.name,
        resource_code=getattr(resource, "resource_code", "") or "",
        kind=str(getattr(resource.kind, "value", resource.kind) or ""),
        worker_type=str(getattr(resource.worker_type, "value", resource.worker_type) or ""),
        employee_id=getattr(resource, "employee_id", None),
        identity_user_id=None,
        is_active=True,
    )
