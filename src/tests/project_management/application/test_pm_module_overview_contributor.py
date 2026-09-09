from __future__ import annotations

from dataclasses import replace

from src.core.application.global_overview.contracts.action_center import ActionCenterContext
from src.core.modules.project_management.application.global_overview.pm_module_overview_contributor import (
    ProjectManagementModuleOverviewContributor,
)
from src.core.platform.domain.security.auth.session import UserSessionPrincipal


def _contributor(services) -> ProjectManagementModuleOverviewContributor:
    return ProjectManagementModuleOverviewContributor(
        platform_runtime_application_service=services["platform_runtime_application_service"],
        dashboard_service=services["dashboard_service"],
        project_service=services["project_service"],
    )


def _context(services) -> ActionCenterContext:
    principal = services["user_session"].principal
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    organization = services["tenant_context_service"].get_active_organization()
    return ActionCenterContext(
        user_id=principal.user_id, tenant_id=tenant_id, organization_id=organization.id
    )


def _plant_principal(services, *, permissions: frozenset[str]):
    default_organization = services["platform_runtime_application_service"].get_active_organization()
    real_user = services["auth_service"].register_user(
        f"pm-module-card-{'-'.join(sorted(permissions)) or 'none'}",
        "StrongPass123",
        role_names=["viewer"],
    )
    active_tenant_id = services["tenant_context_service"].get_active_tenant_id()
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id=real_user.id,
            username=real_user.username,
            display_name="PM Module Card Planner",
            role_names=frozenset(),
            permissions=permissions,
            scoped_access={"organization": {default_organization.id: permissions}},
            active_tenant_id=active_tenant_id,
            active_organization_id=default_organization.id,
        )
    )
    services["user_session"].set_active_organization_id(default_organization.id)


def test_hidden_when_user_lacks_a_project_management_relevant_permission(services):
    assert services["platform_runtime_application_service"].is_enabled("project_management") is True

    _plant_principal(services, permissions=frozenset({"audit.read"}))

    summary = _contributor(services).get_summary(_context(services))

    assert summary is None


def test_visible_when_enabled_and_accessible(services):
    assert services["platform_runtime_application_service"].is_enabled("project_management") is True

    summary = _contributor(services).get_summary(_context(services))

    assert summary is not None
    assert summary.module_code == "project_management"
    assert summary.route_id == "project_management"


def test_summary_text_reuses_the_dashboards_own_active_projects_metric(services):
    organization = services["tenant_context_service"].get_active_organization()
    services["project_service"].create_project(
        "Active PM Module Card Project", financial_currency_code=organization.base_currency
    )

    summary = _contributor(services).get_summary(_context(services))

    assert summary is not None
    portfolio_active = services["dashboard_service"].get_portfolio_data().portfolio.active_projects
    assert summary.summary_text == f"{portfolio_active} active projects"


def test_summary_degrades_gracefully_without_report_view_permission(services):
    _plant_principal(services, permissions=frozenset({"task.read", "project.read"}))

    summary = _contributor(services).get_summary(_context(services))

    assert summary is not None
    assert "project" in summary.summary_text
