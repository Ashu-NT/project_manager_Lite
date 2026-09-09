from __future__ import annotations

from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceIdentityReader,
)


def _tenant_org(services):
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    organization = services["tenant_context_service"].get_active_organization()
    return tenant_id, organization.id


def test_resolves_the_resource_linked_to_a_users_employee_record(services, session):
    tenant_id, organization_id = _tenant_org(services)
    user = services["auth_service"].register_user(
        "identity-owner", "StrongPass123", role_names=["viewer"]
    )
    employee = services["employee_service"].create_employee(
        employee_code="EMP-IDN-1",
        full_name="Identity Owner",
        user_id=user.id,
    )
    resource = services["resource_service"].create_resource(
        "Identity Owner Resource",
        worker_type=WorkerType.EMPLOYEE,
        employee_id=employee.id,
    )

    reader = SqlAlchemyResourceIdentityReader(session=session)
    fact = reader.resolve_resource_for_user(
        user_id=user.id, tenant_id=tenant_id, organization_id=organization_id
    )

    assert fact is not None
    assert fact.resource_id == resource.id
    assert fact.resource_name == resource.name
    assert fact.identity_user_id == user.id
    assert fact.is_active is True


def test_returns_none_for_a_user_with_no_linked_resource(services, session):
    tenant_id, organization_id = _tenant_org(services)
    reader = SqlAlchemyResourceIdentityReader(session=session)

    fact = reader.resolve_resource_for_user(
        user_id="no-such-user", tenant_id=tenant_id, organization_id=organization_id
    )

    assert fact is None


def test_resolves_a_resource_that_is_not_time_reporting_eligible(services, session):
    """The neutral resolver must not apply Timesheets' own eligibility rule
    (kind/worker_type/cost_type) -- that stays a Timesheets-specific concern,
    layered on top of this identity mapping, not baked into it."""
    tenant_id, organization_id = _tenant_org(services)
    user = services["auth_service"].register_user(
        "equipment-owner", "StrongPass123", role_names=["viewer"]
    )
    employee = services["employee_service"].create_employee(
        employee_code="EMP-IDN-2",
        full_name="Equipment Owner",
        user_id=user.id,
    )
    resource = services["resource_service"].create_resource(
        "Owned Equipment",
        worker_type=WorkerType.EMPLOYEE,
        cost_type=CostType.EQUIPMENT,  # not in TimeReportingEligibilityPolicy.ELIGIBLE_COST_TYPES
        employee_id=employee.id,
    )

    reader = SqlAlchemyResourceIdentityReader(session=session)
    fact = reader.resolve_resource_for_user(
        user_id=user.id, tenant_id=tenant_id, organization_id=organization_id
    )

    assert fact is not None
    assert fact.resource_id == resource.id
