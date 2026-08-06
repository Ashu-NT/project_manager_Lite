"""Phase 0A.4 tests — Other independent safety corrections
(docs/pm_modernization/CQRS/project_management_cqrs_existing_state_audit.md, §18 Phase 0A.4).

Covers the three items patched in this phase:
1. `ForecastCostService` now requires explicit tenant/organization context (previously it had no
   `tenant_context_service` at all).
2. `PortfolioDependencyCommandMixin.create_project_dependency` now checks project-scoped
   `portfolio.manage` on both the predecessor and successor project, not just global
   `portfolio.manage` + project-read accessibility.
3. `TaskDependencyDiagnosticsMixin.get_dependency_diagnostics` now requires `task.read` on the
   shared project before returning schedule-impact details.

Broad-exception-to-empty-data fixes (`capacity_pool_builder.py`, `list_task_reservations`,
`_list_pending_approvals`) are exercised implicitly here (a forced failure now propagates instead
of returning an empty tuple) and via the existing Portfolio/Resources/Dashboard test suites, which
already cover the non-failure path for those builders.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth.session import UserSessionPrincipal


# ---------------------------------------------------------------------------
# 1. ForecastCostService requires explicit tenant/organization context.
# ---------------------------------------------------------------------------


def _seed_forecast_project(services):
    project = services["project_service"].create_project(
        "Forecast Safety Project",
        planned_budget=10000.0,
    )
    services["cost_service"].add_cost_item(
        project_id=project.id,
        description="Materials",
        planned_amount=1000.0,
        committed_amount=500.0,
        actual_amount=200.0,
    )
    return project


def test_forecast_service_succeeds_for_authorized_caller_with_context(services):
    project = _seed_forecast_project(services)
    forecast = services["forecast_service"]

    summary = forecast.get_commitment_summary(project.id)

    assert summary.project_id == project.id


class _NoopRepo:
    def list_by_project(self, _project_id):
        return []

    def get(self, _project_id):
        return None


class _AllowAllSession:
    def has_permission(self, _code):
        return True

    def has_scope_permission(self, _scope_type, _scope_id, _code):
        return True


class _MissingOrgTenantContext:
    def require_organization_context(self, *, operation_label):
        raise BusinessRuleError(
            f"Active organization context is required for {operation_label}.",
            code="TENANT_CONTEXT_REQUIRED",
        )


def test_forecast_service_fails_closed_without_tenant_context_service():
    from src.core.modules.project_management.application.financials.forecasts.forecast_service import (
        ForecastCostService,
    )

    service = ForecastCostService(
        cost_repo=_NoopRepo(),
        project_repo=_NoopRepo(),
        user_session=_AllowAllSession(),
        tenant_context_service=None,
    )

    with pytest.raises(BusinessRuleError, match="tenant and organization context") as exc:
        service.get_commitment_summary("does-not-matter")

    assert exc.value.code == "TENANT_CONTEXT_REQUIRED"


def test_forecast_service_fails_closed_without_organization_context():
    from src.core.modules.project_management.application.financials.forecasts.forecast_service import (
        ForecastCostService,
    )

    service = ForecastCostService(
        cost_repo=_NoopRepo(),
        project_repo=_NoopRepo(),
        user_session=_AllowAllSession(),
        tenant_context_service=_MissingOrgTenantContext(),
    )

    with pytest.raises(BusinessRuleError, match="organization context") as exc:
        service.get_commitment_summary("does-not-matter")

    assert exc.value.code == "TENANT_CONTEXT_REQUIRED"


# ---------------------------------------------------------------------------
# 2. Portfolio dependency creation requires project-scoped authorization.
# ---------------------------------------------------------------------------


def test_create_project_dependency_succeeds_for_authorized_caller(services):
    portfolio = services["portfolio_service"]
    project_service = services["project_service"]
    project_a = project_service.create_project("Dependency Auth Project A")
    project_b = project_service.create_project("Dependency Auth Project B")

    dependency = portfolio.create_project_dependency(
        predecessor_project_id=project_a.id,
        successor_project_id=project_b.id,
    )

    assert dependency.predecessor_project_id == project_a.id
    assert dependency.successor_project_id == project_b.id


def test_create_project_dependency_denies_caller_without_project_scope(services):
    portfolio = services["portfolio_service"]
    project_service = services["project_service"]
    project_a = project_service.create_project("Dependency Scope Project A")
    project_b = project_service.create_project("Dependency Scope Project B")
    principal = services["user_session"].principal
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id=principal.user_id,
            username="restricted-planner",
            display_name="Restricted Planner",
            role_names=frozenset(),
            permissions=frozenset({"portfolio.manage", "project.read"}),
            scoped_access={
                "project": {
                    project_a.id: frozenset({"project.read"}),
                    project_b.id: frozenset({"project.read"}),
                },
            },
            active_tenant_id=principal.active_tenant_id,
            active_organization_id=principal.active_organization_id,
        )
    )

    with pytest.raises(BusinessRuleError, match="Permission denied") as exc:
        portfolio.create_project_dependency(
            predecessor_project_id=project_a.id,
            successor_project_id=project_b.id,
        )

    assert exc.value.code == "PERMISSION_DENIED"


# ---------------------------------------------------------------------------
# 3. TaskService.get_dependency_diagnostics requires task.read on the project.
# ---------------------------------------------------------------------------


def _seed_diagnostics_tasks(services):
    project = services["project_service"].create_project("Diagnostics Auth Project")
    task_service = services["task_service"]
    predecessor = task_service.create_task(
        project.id, "Predecessor", start_date=date(2026, 3, 2), duration_days=3
    )
    successor = task_service.create_task(
        project.id, "Successor", start_date=date(2026, 3, 5), duration_days=3
    )
    return project, predecessor, successor


def test_get_dependency_diagnostics_succeeds_for_authorized_caller(services):
    _project, predecessor, successor = _seed_diagnostics_tasks(services)
    task_service = services["task_service"]

    diagnostic = task_service.get_dependency_diagnostics(predecessor.id, successor.id)

    assert diagnostic.predecessor_task_id == predecessor.id
    assert diagnostic.successor_task_id == successor.id


def test_get_dependency_diagnostics_denies_caller_without_project_scope(services):
    _project, predecessor, successor = _seed_diagnostics_tasks(services)
    task_service = services["task_service"]
    principal = services["user_session"].principal
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id=principal.user_id,
            username="restricted-planner",
            display_name="Restricted Planner",
            role_names=frozenset(),
            permissions=frozenset({"task.read"}),
            scoped_access={"project": {"other-project-unrelated": frozenset({"portfolio.manage", "task.read"})}},
            active_tenant_id=principal.active_tenant_id,
            active_organization_id=principal.active_organization_id,
        )
    )

    with pytest.raises(BusinessRuleError, match="Permission denied") as exc:
        task_service.get_dependency_diagnostics(predecessor.id, successor.id)

    assert exc.value.code == "PERMISSION_DENIED"


# ---------------------------------------------------------------------------
# Broad-exception fixes now propagate instead of swallowing into empty data.
# ---------------------------------------------------------------------------


def test_capacity_pool_builder_propagates_failure_instead_of_swallowing(services, monkeypatch):
    from src.core.modules.project_management.api.desktop.portfolio.builders.capacity_pool_builder import (
        build_capacity_pool,
    )

    pool_service = services["portfolio_resource_pool_service"]

    def _boom(*_args, **_kwargs):
        raise RuntimeError("forced failure for Phase 0A.4 broad-exception test")

    monkeypatch.setattr(pool_service, "get_pool_report", _boom)

    with pytest.raises(RuntimeError, match="forced failure"):
        build_capacity_pool(pool_service)


def test_dashboard_pending_approvals_propagates_failure_instead_of_swallowing():
    from src.core.modules.project_management.api.desktop.dashboard.services.dashboard_snapshot_service import (
        DashboardSnapshotService,
    )

    class _BoomApprovalService:
        def list_pending(self, *_args, **_kwargs):
            raise RuntimeError("forced failure for Phase 0A.4 broad-exception test")

    service = DashboardSnapshotService.__new__(DashboardSnapshotService)
    service._approval_service = _BoomApprovalService()

    with pytest.raises(RuntimeError, match="forced failure"):
        service._list_pending_approvals(project_id=None)
