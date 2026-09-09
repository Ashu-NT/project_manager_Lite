from __future__ import annotations

from dataclasses import replace

from src.core.application.global_overview.contracts.action_center import ActionCenterContext
from src.core.platform.application.global_overview.platform_module_overview_contributor import (
    PlatformModuleOverviewContributor,
)


def _contributor(services) -> PlatformModuleOverviewContributor:
    return PlatformModuleOverviewContributor(approval_service=services["approval_service"])


def _context(services) -> ActionCenterContext:
    principal = services["user_session"].principal
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    organization = services["tenant_context_service"].get_active_organization()
    return ActionCenterContext(
        user_id=principal.user_id, tenant_id=tenant_id, organization_id=organization.id
    )


def test_platform_summary_is_returned_using_platform_access_semantics_not_module_policy(services):
    """Platform is not an EnterpriseModule -- its card must still render
    regardless of module enable/license state, per its own access rule."""
    summary = _contributor(services).get_summary(_context(services))

    assert summary is not None
    assert summary.module_code == "platform"
    assert summary.route_id == "platform"


def test_summary_text_reflects_the_real_pending_approval_count(services):
    services["approval_service"].request_change(
        request_type="organization_request",
        entity_type="organization_request",
        entity_id="org-request-module-card-1",
        project_id=None,
    )
    services["approval_service"].request_change(
        request_type="organization_request",
        entity_type="organization_request",
        entity_id="org-request-module-card-2",
        project_id=None,
    )

    summary = _contributor(services).get_summary(_context(services))

    assert summary is not None
    assert summary.summary_text == "2 items require attention"


def test_summary_degrades_gracefully_without_approval_permission(services):
    user_session = services["user_session"]
    user_session.set_principal(replace(user_session.principal, permissions=frozenset()))

    summary = _contributor(services).get_summary(_context(services))

    assert summary is not None
    assert summary.summary_text == "Shared administration and governance"
