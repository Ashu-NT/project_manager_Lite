"""Phase 0A.1 tests — Portfolio resource-report authorization
(docs/pm_modernization/CQRS/project_management_cqrs_existing_state_audit.md, §18 Phase 0A.1).

``PortfolioResourcePoolService`` was found, during this phase, to have never been constructed
anywhere in production composition (confirmed by a repo-wide grep for the class name returning
zero matches before this phase's fix). These tests exercise the service directly — the same
object now returned by the real composition graph under the ``"portfolio_resource_pool_service"``
key — to prove both the new authorization guard and the (newly-completed) composition wiring
work correctly.

Tests that only need permission/tenant-context control use hand-built fakes, mirroring the
established convention in ``test_tenant_isolation_services_pm.py``. Tests that need to prove the
composition wiring and the desktop DTO boundary are unaffected use the real ``services`` fixture
(the actual production composition graph via ``build_service_dict``).
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.core.modules.project_management.api.desktop.portfolio.builders.capacity_pool_builder import (
    build_capacity_pool,
)
from src.core.modules.project_management.application.resources.portfolio_resource_pool_service import (
    PortfolioResourcePoolService,
)
from src.core.modules.project_management.contracts.reads.portfolio.models.resource_pool_facts import (
    PortfolioResourceFact,
    PortfolioResourcePoolFacts,
)
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.application.tenant.tenancy.context_policy import SaaSTenantContextPolicy
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.domain.tenant.tenancy.tenant import Tenant

_FROM_DATE = date(2026, 1, 5)
_TO_DATE = date(2026, 3, 5)


# ---------------------------------------------------------------------------
# Fakes (mirroring test_tenant_isolation_services_pm.py's established convention:
# real TenantContextService + real domain objects, fake repositories only)
# ---------------------------------------------------------------------------


class _TenantRepo:
    def __init__(self, tenants: list[Tenant]) -> None:
        self._tenants = {t.id: t for t in tenants}

    def get(self, tenant_id: str):
        return self._tenants.get(tenant_id)

    def get_default(self):
        return None


class _OrgRepo:
    def __init__(self, organizations: list[Organization]) -> None:
        self._organizations = {o.id: o for o in organizations}

    def get(self, organization_id: str):
        return self._organizations.get(organization_id)


class _ResourcePoolReader:
    def __init__(self, resources: list[Resource]) -> None:
        self.rows = list(resources)

    def read_facts(
        self,
        *,
        tenant_id,
        organization_id,
        from_date,
        to_date,
        resource_ids=None,
    ):
        selected = [
            resource
            for resource in self.rows
            if resource.organization_id == organization_id
            and (resource_ids is None or resource.id in resource_ids)
        ]
        return PortfolioResourcePoolFacts(
            tenant_id=tenant_id,
            organization_id=organization_id,
            resources=tuple(
                PortfolioResourceFact(
                    resource_id=resource.id,
                    name=resource.name,
                    capacity_percent=resource.capacity_percent,
                )
                for resource in selected
            ),
            demands=(),
        )


class _Calendar:
    def is_working_day(self, target_date: date) -> bool:
        return target_date.weekday() < 5

    def working_days_between(self, from_date: date, to_date: date) -> int:
        return max(0, (to_date - from_date).days)


def _principal(
    *,
    permissions: frozenset[str],
    active_tenant_id: str | None,
    active_organization_id: str | None,
) -> UserSessionPrincipal:
    return UserSessionPrincipal(
        user_id="user-1",
        username="tester",
        display_name="Tester",
        role_names=frozenset({"admin"}),
        permissions=permissions,
        active_tenant_id=active_tenant_id,
        active_organization_id=active_organization_id,
    )


def _build_service(
    *,
    resources: list[Resource],
    tenants: list[Tenant],
    organizations: list[Organization],
    active_tenant_id: str | None,
    active_organization_id: str | None,
    permissions: frozenset[str] = frozenset({"portfolio.read"}),
) -> PortfolioResourcePoolService:
    session = UserSessionContext()
    session.set_principal(
        _principal(
            permissions=permissions,
            active_tenant_id=active_tenant_id,
            active_organization_id=active_organization_id,
        )
    )
    tenant_context = TenantContextService(
        tenant_repo=_TenantRepo(tenants),
        organization_repo=_OrgRepo(organizations),
        user_session=session,
        context_policy=SaaSTenantContextPolicy(),
    )
    return PortfolioResourcePoolService(
        reader=_ResourcePoolReader(resources),
        calendar=_Calendar(),
        tenant_context_service=tenant_context,
        user_session=session,
    )


# ---------------------------------------------------------------------------
# 1. Authorized caller receives the existing report, unchanged.
# ---------------------------------------------------------------------------


def test_authorized_caller_receives_pool_report(services) -> None:
    resource = services["resource_service"].create_resource("Pool Resource", "Developer", hourly_rate=75.0)
    pool_service = services["portfolio_resource_pool_service"]
    assert isinstance(pool_service, PortfolioResourcePoolService)

    report = pool_service.get_pool_report(_FROM_DATE, _TO_DATE)

    assert report.from_date == _FROM_DATE
    assert report.to_date == _TO_DATE
    assert {summary.resource_id for summary in report.pool} == {resource.id}


# ---------------------------------------------------------------------------
# 2. Caller without permission receives the typed permission error.
# ---------------------------------------------------------------------------


def test_caller_without_portfolio_read_permission_is_denied(services) -> None:
    services["resource_service"].create_resource("Pool Resource", "Developer", hourly_rate=75.0)
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id="u-no-portfolio",
            username="pm-reader",
            display_name="PM Reader",
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"project.read"}),
        )
    )
    pool_service = services["portfolio_resource_pool_service"]

    with pytest.raises(BusinessRuleError, match="Permission denied") as exc:
        pool_service.get_pool_report(_FROM_DATE, _TO_DATE)

    assert exc.value.code == "PERMISSION_DENIED"

    with pytest.raises(BusinessRuleError) as exc_demand:
        pool_service.get_resource_demand_by_project("does-not-matter", _FROM_DATE, _TO_DATE)

    assert exc_demand.value.code == "PERMISSION_DENIED"


# ---------------------------------------------------------------------------
# 3. Missing tenant context fails closed.
# ---------------------------------------------------------------------------


def test_missing_tenant_context_fails_closed() -> None:
    org = Organization.create("ORG-A", "Org A", tenant_id="tenant-a")
    resource = Resource(id="res-a", name="Resource A", organization_id=org.id)
    service = _build_service(
        resources=[resource],
        tenants=[],
        organizations=[org],
        active_tenant_id=None,
        active_organization_id=None,
    )

    with pytest.raises(BusinessRuleError, match="Active tenant context") as exc:
        service.get_pool_report(_FROM_DATE, _TO_DATE)

    assert exc.value.code == "TENANT_CONTEXT_REQUIRED"


# ---------------------------------------------------------------------------
# 4. Missing organization context fails closed.
# ---------------------------------------------------------------------------


def test_missing_organization_context_fails_closed() -> None:
    tenant_a = Tenant.create("TEN-A", "Tenant A")
    org = Organization.create("ORG-A", "Org A", tenant_id=tenant_a.id)
    resource = Resource(id="res-a", name="Resource A", organization_id=org.id)
    service = _build_service(
        resources=[resource],
        tenants=[tenant_a],
        organizations=[org],
        active_tenant_id=tenant_a.id,
        active_organization_id=None,
    )

    with pytest.raises(BusinessRuleError, match="Active organization context") as exc:
        service.get_pool_report(_FROM_DATE, _TO_DATE)

    assert exc.value.code == "ORGANIZATION_CONTEXT_REQUIRED"


# ---------------------------------------------------------------------------
# 5. Another tenant's data is never returned.
# ---------------------------------------------------------------------------


def test_cross_tenant_resource_never_returned() -> None:
    tenant_a = Tenant.create("TEN-A", "Tenant A")
    tenant_b = Tenant.create("TEN-B", "Tenant B")
    org_a = Organization.create("ORG-A", "Org A", tenant_id=tenant_a.id)
    org_b = Organization.create("ORG-B", "Org B", tenant_id=tenant_b.id)
    resource_a = Resource(id="res-a", name="Resource A", organization_id=org_a.id)
    resource_b = Resource(id="res-b", name="Resource B (other tenant)", organization_id=org_b.id)
    service = _build_service(
        resources=[resource_a, resource_b],
        tenants=[tenant_a, tenant_b],
        organizations=[org_a, org_b],
        active_tenant_id=tenant_a.id,
        active_organization_id=org_a.id,
    )

    report = service.get_pool_report(_FROM_DATE, _TO_DATE)

    resource_ids = {summary.resource_id for summary in report.pool}
    assert resource_ids == {resource_a.id}
    assert resource_b.id not in resource_ids


# ---------------------------------------------------------------------------
# 6. Another organization's data is never returned.
# ---------------------------------------------------------------------------


def test_cross_organization_resource_never_returned() -> None:
    tenant_a = Tenant.create("TEN-A", "Tenant A")
    org_a = Organization.create("ORG-A", "Org A", tenant_id=tenant_a.id)
    org_a2 = Organization.create("ORG-A2", "Org A2", tenant_id=tenant_a.id)
    resource_a = Resource(id="res-a", name="Resource A", organization_id=org_a.id)
    resource_a2 = Resource(id="res-a2", name="Resource A2 (other org)", organization_id=org_a2.id)
    service = _build_service(
        resources=[resource_a, resource_a2],
        tenants=[tenant_a],
        organizations=[org_a, org_a2],
        active_tenant_id=tenant_a.id,
        active_organization_id=org_a.id,
    )

    report = service.get_pool_report(_FROM_DATE, _TO_DATE)

    resource_ids = {summary.resource_id for summary in report.pool}
    assert resource_ids == {resource_a.id}
    assert resource_a2.id not in resource_ids


# ---------------------------------------------------------------------------
# 7. Desktop DTO remains field-for-field unchanged for an authorized caller.
# ---------------------------------------------------------------------------


def test_desktop_dto_unchanged_for_authorized_caller(services) -> None:
    resource = services["resource_service"].create_resource("Pool Resource", "Developer", hourly_rate=75.0)
    pool_service = services["portfolio_resource_pool_service"]
    today = date.today()
    to_date = today + timedelta(days=90)

    report = pool_service.get_pool_report(from_date=today, to_date=to_date)
    dtos = build_capacity_pool(pool_service)

    assert len(dtos) == len(report.pool)
    by_id = {summary.resource_id: summary for summary in report.pool}
    for dto in dtos:
        summary = by_id[dto.resource_id]
        assert dto.resource_name == (summary.resource_name or summary.resource_id or "Resource")
        assert dto.peak_load_percent == float(summary.peak_load_percent or 0.0)
        assert dto.average_load_percent == float(summary.average_load_percent or 0.0)
        assert dto.overloaded == bool(summary.overloaded)
    assert resource.id in by_id
