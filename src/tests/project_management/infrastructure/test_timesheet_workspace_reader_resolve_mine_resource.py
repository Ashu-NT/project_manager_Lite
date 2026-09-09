from __future__ import annotations

from src.core.modules.project_management.domain.enums import CostType, WorkerType
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


def test_resolve_mine_resource_still_resolves_a_time_reporting_eligible_resource(
    services, session
):
    """Behavior-preservation: same result as before the delegation refactor
    for the common, time-reporting-eligible case."""
    tenant_id, organization_id = _tenant_org(services)
    user = services["auth_service"].register_user(
        "timesheet-owner", "StrongPass123", role_names=["viewer"]
    )
    employee = services["employee_service"].create_employee(
        employee_code="EMP-TS-1",
        full_name="Timesheet Owner",
        user_id=user.id,
    )
    resource = services["resource_service"].create_resource(
        "Timesheet Owner Resource",
        worker_type=WorkerType.EMPLOYEE,
        cost_type=CostType.LABOR,
        employee_id=employee.id,
    )

    fact = _reader(session).resolve_mine_resource(
        user_id=user.id, tenant_id=tenant_id, organization_id=organization_id
    )

    assert fact is not None
    assert fact.resource_id == resource.id
    assert fact.identity_user_id == user.id


def test_resolve_mine_resource_still_excludes_a_time_reporting_ineligible_resource(
    services, session
):
    """The neutral resolver would find this resource; the Timesheets-owned
    eligibility check layered on top must still reject it, unchanged."""
    tenant_id, organization_id = _tenant_org(services)
    user = services["auth_service"].register_user(
        "equipment-owner-2", "StrongPass123", role_names=["viewer"]
    )
    employee = services["employee_service"].create_employee(
        employee_code="EMP-TS-2",
        full_name="Equipment Owner Two",
        user_id=user.id,
    )
    services["resource_service"].create_resource(
        "Owned Equipment Two",
        worker_type=WorkerType.EMPLOYEE,
        cost_type=CostType.EQUIPMENT,
        employee_id=employee.id,
    )

    fact = _reader(session).resolve_mine_resource(
        user_id=user.id, tenant_id=tenant_id, organization_id=organization_id
    )

    assert fact is None


def test_resolve_mine_resource_returns_none_for_unknown_user(services, session):
    tenant_id, organization_id = _tenant_org(services)

    fact = _reader(session).resolve_mine_resource(
        user_id="no-such-user", tenant_id=tenant_id, organization_id=organization_id
    )

    assert fact is None
