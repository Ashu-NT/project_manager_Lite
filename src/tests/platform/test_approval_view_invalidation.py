from __future__ import annotations

import inspect

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.approval.event_handlers.view_invalidation import (
    APPROVAL_CATEGORY,
    APPROVAL_REQUESTS_SCOPE_CODE,
    build_approval_view_invalidation_handler,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.approval import (
    ApprovalApproved,
    ApprovalRejected,
    ApprovalRequested,
    ApprovalStatus,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    AllTenants,
    ExactOrganization,
    OrganizationScope,
    TenantWide,
)
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.adapters.approval_view_invalidation_adapter import (
    ApprovalViewInvalidationAdapter,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _pm_catalog(services) -> ProjectManagementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)


def _active_tenant(services) -> str:
    return services["tenant_context_service"].get_active_tenant_id()


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _login_as_fresh_requester(services) -> None:
    username = _unique("viewinv-requester")
    services["auth_service"].register_user(username, "StrongPass123", role_names=["planner"])
    _login(services, username, "StrongPass123")


def _submitted_budget(services, session):
    _login(services, "admin", "ChangeMe123!")
    project = services["project_service"].create_project(
        _unique("View Invalidation Project"),
        code=_unique("VI-PRJ"),
        financial_currency_code="USD",
    )
    budget_service = services["budget_service"]
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=_unique("VI-CC"), name="View invalidation cost code"
    )
    budget = budget_service.create_budget(project.id, "View Invalidation Budget")
    budget_service.add_line(
        budget.id, cost_code_id=cost_code.id, description="Line 1", amount=1000,
        expected_budget_version=budget.row_version,
    )
    budget = budget_service.get_budget(budget.id)
    budget = budget_service.submit_budget(
        budget.id, submitted_by="admin", expected_version=budget.row_version
    )
    session.expire_all()
    return project, budget


def _request_budget_approval_as_a_different_user(services, budget):
    # P10A: a fresh login's active-organization auto-select is genuinely ambiguous once more than
    # one organization is enabled simultaneously (no longer "the one enabled org", unlike the
    # pre-P10A mutual-exclusion model) -- pin it explicitly to whatever was active immediately
    # before the switch rather than relying on that heuristic.
    active_organization_id = services["tenant_context_service"].get_active_organization_id()
    _login_as_fresh_requester(services)
    if active_organization_id:
        services["user_session"].set_active_organization_id(active_organization_id)
    approvals = services["approval_service"]
    request = approvals.request_change(
        request_type="budget.approve",
        entity_type="project_budget",
        entity_id=budget.id,
        project_id=budget.project_id,
        payload={"budget_id": budget.id, "expected_version": budget.row_version, "notes": ""},
    )
    _login(services, "admin", "ChangeMe123!")
    return request


def _strip_strings_and_comments(source: str) -> str:
    """Drop triple-quoted docstrings, string literals, and `#` comments so a structural scan
    only sees actual code, not prose that happens to mention a forbidden call/name."""
    import re

    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", source)
    no_comments = re.sub(r"#.*", "", no_docstrings)
    return no_comments


def _imported_module_names(module) -> set[str]:
    import ast

    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


# ---------------------------------------------------------------------------
# Mapper: all three events -> the SAME target, exact scope, no extra hints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event",
    [
        ApprovalRequested(
            approval_id="a-1", tenant_id="t-1", organization_id="o-1", approval_type="budget.approve",
            entity_type="project_budget", entity_id="budget-1", requested_by_user_id="u-1",
            occurred_at=None,
        ),
        ApprovalApproved(
            approval_id="a-1", tenant_id="t-1", organization_id="o-1", approval_type="budget.approve",
            entity_type="project_budget", entity_id="budget-1", decided_by_user_id="u-2",
            occurred_at=None,
        ),
        ApprovalRejected(
            approval_id="a-1", tenant_id="t-1", organization_id="o-1", approval_type="budget.approve",
            entity_type="project_budget", entity_id="budget-1", decided_by_user_id="u-2",
            occurred_at=None,
        ),
    ],
)
def test_mapper_produces_exactly_one_approval_requests_hint_per_event(event):
    hints = []

    class _FakeChannel:
        def notify(self, hint):
            hints.append(hint)

    handler = build_approval_view_invalidation_handler(_FakeChannel())
    handler(event, DomainEventContext(correlation_id="corr-1"))

    assert len(hints) == 1
    hint = hints[0]
    assert hint.scope == OrganizationScope("t-1", "o-1")
    assert hint.category == APPROVAL_CATEGORY
    assert hint.scope_code == APPROVAL_REQUESTS_SCOPE_CODE
    assert hint.entity_type == "approval_request"
    assert hint.entity_id == "a-1"


def test_approval_view_invalidation_mapper_has_no_qt_dependency():
    import src.core.platform.application.approval.event_handlers.view_invalidation as mapper_module

    imports = _imported_module_names(mapper_module)
    for forbidden in ("PySide6", "QtCore", "ui_qml", "domain_events"):
        assert not any(forbidden in name for name in imports), imports


def test_approval_view_invalidation_adapter_has_no_domain_event_import():
    import src.ui_qml.platform.adapters.approval_view_invalidation_adapter as adapter_module

    imports = _imported_module_names(adapter_module)
    for forbidden in ("domain_events", "sqlalchemy"):
        assert not any(forbidden in name for name in imports), imports
    source = _strip_strings_and_comments(inspect.getsource(adapter_module))
    for forbidden in ("ApprovalRequested", "ApprovalApproved", "ApprovalRejected", "DomainEvent"):
        assert forbidden not in source


def test_control_workspace_controller_does_not_import_domain_event_vocabulary():
    """§10: controllers must not import ApprovalRequested/ApprovalApproved/ApprovalRejected/
    DomainEvent/ViewInvalidationHint/ScopeFilter/EventScope/postcommit bus."""
    import src.ui_qml.platform.controllers.control.control_workspace_controller as controller_module

    source = inspect.getsource(controller_module)
    for forbidden in (
        "ApprovalRequested", "ApprovalApproved", "ApprovalRejected", "DomainEvent",
        "ViewInvalidationHint", "ScopeFilter", "EventScope", "PostCommitEventPublisher",
    ):
        assert forbidden not in source


def test_collaboration_workspace_controller_does_not_import_domain_event_vocabulary():
    import src.ui_qml.modules.project_management.controllers.collaboration.collaboration_workspace_controller as controller_module

    source = inspect.getsource(controller_module)
    for forbidden in (
        "ApprovalRequested", "ApprovalApproved", "ApprovalRejected", "DomainEvent",
        "ViewInvalidationHint", "ScopeFilter", "EventScope", "PostCommitEventPublisher",
    ):
        assert forbidden not in source


# ---------------------------------------------------------------------------
# End-to-end: real Approval commands -> real Control workspace UI
# ---------------------------------------------------------------------------


def test_standalone_request_change_refreshes_control_workspace_exactly_once(services, session):
    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh_approvals = lambda: refresh_calls.append("approvals") or None
    _login_as_fresh_requester(services)

    services["approval_service"].request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id=_unique("standalone-ui-probe"),
        project_id=None,
        payload={"name": "Standalone UI probe"},
    )

    assert refresh_calls == ["approvals"]


def test_host_workflow_submit_change_refreshes_control_workspace_exactly_once(services):
    from datetime import date
    from decimal import Decimal

    from src.core.modules.project_management.domain.financials.financial_change import (
        FinancialChangeImpactType,
    )

    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh_approvals = lambda: refresh_calls.append("approvals") or None

    _login(services, "admin", "ChangeMe123!")
    project = services["project_service"].create_project(
        _unique("View Invalidation Finance Project"), financial_currency_code="USD"
    )
    code = services["financial_configuration_service"].create_cost_code(
        code=_unique("VI-FIN-CC"), name="View invalidation finance cost code"
    )
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "VI approved budget")
    budget_line = budgets.add_line(
        budget.id, cost_code_id=code.id, description="Approved scope", amount=Decimal("100"),
        expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(budget.id, "admin", expected_version=budget.row_version)
    budgets.approve_budget(budget.id, approved_by="admin", expected_version=budget.row_version)
    refresh_calls.clear()  # the approve_budget decision above also invalidates -- isolate submit_change's own

    changes = services["financial_change_service"]
    change = changes.create_change(
        project.id, title="VI change", reason="VI probe",
        effective_date=date(2026, 8, 11), created_by="admin",
    )
    changes.add_impact(
        change.id, impact_type=FinancialChangeImpactType.BUDGET, description="Increase scope",
        amount=Decimal("10"), cost_code_id=code.id, target_line_id=budget_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)

    changes.submit_change(change.id, submitted_by="admin", expected_version=change.row_version)

    assert refresh_calls == ["approvals"]


def test_approve_and_apply_refreshes_control_workspace_exactly_once_no_legacy_signal(
    services, session
):
    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh_approvals = lambda: refresh_calls.append("approvals") or None

    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    refresh_calls.clear()

    decided = services["approval_service"].approve_and_apply(request.id, note="Approved")

    assert decided.status == ApprovalStatus.APPROVED
    assert refresh_calls == ["approvals"]
    assert not hasattr(__import__(
        "src.core.shared.events.domain_events", fromlist=["domain_events"]
    ).domain_events, "approvals_changed")


def test_reject_refreshes_control_workspace_exactly_once(services, session):
    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh_approvals = lambda: refresh_calls.append("approvals") or None

    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    refresh_calls.clear()

    decided = services["approval_service"].reject(request.id, note="Rejected")

    assert decided.status == ApprovalStatus.REJECTED
    assert refresh_calls == ["approvals"]


def test_refresh_approvals_does_not_touch_the_unrelated_audit_feed(services, session):
    """§14/§18: the narrow Control reaction must not force the genuinely unrelated audit-feed
    read model to re-fetch. Uses a standalone `request_change` (no project creation) so the
    pre-existing, unrelated `project_changed` subscription (out of scope for Approval-P3) cannot
    confound this Approval-only isolation check."""
    catalog = _catalog(services)
    control = catalog.controlWorkspace
    control.ensureLoaded()
    audit_calls = []
    control._set_audit_feed = lambda *a, **k: audit_calls.append("audit") or None
    _login_as_fresh_requester(services)

    services["approval_service"].request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id=_unique("audit-isolation-probe"),
        project_id=None,
        payload={"name": "Audit isolation probe"},
    )

    assert audit_calls == []


def test_control_workspace_approval_refresh_respects_lazy_loading(services, session):
    """Replaces the removed `_CASES` entry in `test_secondary_workspace_lazy_loading.py`: an
    unvisited (`_loaded is False`) Control workspace must not be force-loaded by an Approval
    invalidation; once visited, it reacts. Uses standalone `request_change` calls (no project
    creation) so the pre-existing, unrelated `project_changed` subscription cannot confound the
    exactly-once assertion below."""
    catalog = _catalog(services)
    control = catalog.controlWorkspace
    assert control._loaded is False
    approval_calls = []
    control._refresh_approval_state = lambda: approval_calls.append("state") or None
    _login_as_fresh_requester(services)

    services["approval_service"].request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id=_unique("lazy-loading-probe-1"),
        project_id=None,
        payload={"name": "Lazy loading probe 1"},
    )
    assert approval_calls == [], "an unvisited workspace must not be force-loaded"
    assert control._loaded is False

    control.ensureLoaded()
    approval_calls.clear()
    services["approval_service"].request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id=_unique("lazy-loading-probe-2"),
        project_id=None,
        payload={"name": "Lazy loading probe 2"},
    )
    assert approval_calls == ["state"]


# ---------------------------------------------------------------------------
# End-to-end: real Approval commands -> real PM Collaboration UI
# ---------------------------------------------------------------------------


def test_standalone_request_change_refreshes_pm_collaboration_workspace(services):
    pm_catalog = _pm_catalog(services)
    collaboration = pm_catalog.collaborationWorkspace
    refresh_calls = []
    collaboration.refresh = lambda: refresh_calls.append("refresh")
    _login_as_fresh_requester(services)

    services["approval_service"].request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id=_unique("pm-ui-probe"),
        project_id=None,
        payload={"name": "PM collaboration UI probe"},
    )

    assert refresh_calls == ["refresh"]


def test_pm_dashboard_no_longer_reacts_to_approval_mutations(services):
    """Approval-P3: the incidental `approval_request`/`platform` subscription is dropped, not
    migrated -- this dashboard's own `build_workspace_state(...)` never reads Approval data."""
    pm_catalog = _pm_catalog(services)
    dashboard = pm_catalog.dashboardWorkspace
    refresh_calls = []
    dashboard.refresh = lambda: refresh_calls.append("refresh")
    _login_as_fresh_requester(services)

    services["approval_service"].request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id=_unique("pm-dashboard-probe"),
        project_id=None,
        payload={"name": "PM dashboard probe"},
    )

    assert refresh_calls == []


# ---------------------------------------------------------------------------
# Adapter: organization scope, no AllTenants/TenantWide
# ---------------------------------------------------------------------------


def test_adapter_only_reacts_to_its_exact_active_organization(services, session):
    channel = services["platform_view_invalidation_channel"]
    organization_service = services["organization_service"]
    tenant_id = _active_tenant(services)
    org_a1 = services["tenant_context_service"].get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique("VI-SCOPE-A2"), display_name="View Invalidation Org A2", is_enabled=False
    )

    adapter = ApprovalViewInvalidationAdapter(channel=channel, tenant_id=tenant_id, organization_id=org_a1.id)
    signal_calls = []
    adapter.approvalsStale.connect(lambda: signal_calls.append("stale"))

    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    assert request.organization_id == org_a1.id
    assert signal_calls == ["stale"], "the active org's own Approval request must be observed"

    signal_calls.clear()
    organization_service.enable_organization(org_a2.id)
    services["tenant_context_service"].set_active_organization(org_a2.id)
    _, budget2 = _submitted_budget(services, session)
    request2 = _request_budget_approval_as_a_different_user(services, budget2)
    assert request2.organization_id == org_a2.id
    assert signal_calls == [], "Org A2's own request must not stale an adapter still scoped to A1"

    adapter.dispose()


def test_adapter_never_subscribes_via_all_tenants_or_tenant_wide(services):
    channel = services["platform_view_invalidation_channel"]
    tenant_id = _active_tenant(services)
    org = services["tenant_context_service"].get_active_organization()

    adapter = ApprovalViewInvalidationAdapter(channel=channel, tenant_id=tenant_id, organization_id=org.id)
    try:
        filters = [filt for filt, _handler in channel._subscriptions.values()]
        assert not any(isinstance(f, (AllTenants, TenantWide)) for f in filters)
        exact_filters = [f for f in filters if isinstance(f, ExactOrganization)]
        assert any(f.tenant_id == tenant_id and f.organization_id == org.id for f in exact_filters)
    finally:
        adapter.dispose()


def test_adapter_with_no_channel_or_empty_scope_is_inert():
    inert_no_channel = ApprovalViewInvalidationAdapter(channel=None, tenant_id="t-1", organization_id="o-1")
    calls = []
    inert_no_channel.approvalsStale.connect(lambda: calls.append("stale"))
    inert_no_channel._on_hint.__self__  # smoke: attribute exists
    inert_no_channel.dispose()

    class _FakeChannel:
        def __init__(self):
            self.subscriptions = 0

        def subscribe(self, filt, handler):
            self.subscriptions += 1

            class _Sub:
                def dispose(self_inner):
                    pass

            return _Sub()

    fake_channel = _FakeChannel()
    inert_empty_scope = ApprovalViewInvalidationAdapter(channel=fake_channel, tenant_id="", organization_id="")
    assert fake_channel.subscriptions == 0
    inert_empty_scope.dispose()


# ---------------------------------------------------------------------------
# Switch lifecycle: organization switch and tenant switch, no stale/duplicate subscription
# ---------------------------------------------------------------------------


def test_adapter_follows_an_organization_switch_with_no_stale_or_duplicate_subscription(
    services, session
):
    channel = services["platform_view_invalidation_channel"]
    organization_service = services["organization_service"]
    tenant_id = _active_tenant(services)
    org_a1 = services["tenant_context_service"].get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique("VI-SWITCH-A2"), display_name="Switch Org A2", is_enabled=False
    )

    adapter = ApprovalViewInvalidationAdapter(channel=channel, tenant_id=tenant_id, organization_id=org_a1.id)
    signal_calls = []
    adapter.approvalsStale.connect(lambda: signal_calls.append("stale"))
    subscription_count_before = len(channel._subscriptions)

    _, budget_a1 = _submitted_budget(services, session)
    _request_budget_approval_as_a_different_user(services, budget_a1)
    assert signal_calls == ["stale"]

    organization_service.enable_organization(org_a2.id)
    services["tenant_context_service"].set_active_organization(org_a2.id)
    adapter.set_active_scope(tenant_id=tenant_id, organization_id=org_a2.id)
    assert len(channel._subscriptions) == subscription_count_before, (
        "switching must dispose the old subscription before adding the new one -- never accumulate"
    )

    signal_calls.clear()
    _, budget_a2 = _submitted_budget(services, session)
    request_a2 = _request_budget_approval_as_a_different_user(services, budget_a2)
    assert request_a2.organization_id == org_a2.id
    assert signal_calls == ["stale"]

    adapter.dispose()
    assert len(channel._subscriptions) == subscription_count_before - 1


def test_full_switch_sequence_a1_a2_b1_a1_ends_with_exactly_one_live_subscription(services):
    """§37: A/A1 -> A/A2 -> B/B1 -> A/A1 -- exactly one live subscription throughout, correct
    final scope, no duplicate callbacks."""
    channel = services["platform_view_invalidation_channel"]
    organization_service = services["organization_service"]
    tenant_admin = services["tenant_admin_service"]
    tenant_a = _active_tenant(services)
    org_a1 = services["tenant_context_service"].get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique("VI-SEQ-A2"), display_name="Sequence Org A2", is_enabled=False
    )
    tenant_b = tenant_admin.create_tenant(_unique("VI-SEQ-TENANT-B"), "Sequence Tenant B")

    adapter = ApprovalViewInvalidationAdapter(channel=channel, tenant_id=tenant_a, organization_id=org_a1.id)
    baseline_subscription_count = len(channel._subscriptions)

    def _live_exact_filters():
        return [f for f, _h in channel._subscriptions.values() if isinstance(f, ExactOrganization)]

    assert any(f.tenant_id == tenant_a and f.organization_id == org_a1.id for f in _live_exact_filters())

    adapter.set_active_scope(tenant_id=tenant_a, organization_id=org_a2.id)
    assert len(channel._subscriptions) == baseline_subscription_count
    filters_now = _live_exact_filters()
    assert any(f.tenant_id == tenant_a and f.organization_id == org_a2.id for f in filters_now)
    assert not any(f.organization_id == org_a1.id for f in filters_now)

    adapter.set_active_scope(tenant_id=tenant_b.id, organization_id="b1-placeholder")
    assert len(channel._subscriptions) == baseline_subscription_count
    filters_now = _live_exact_filters()
    assert any(f.tenant_id == tenant_b.id and f.organization_id == "b1-placeholder" for f in filters_now)
    assert not any(f.tenant_id == tenant_a for f in filters_now)

    adapter.set_active_scope(tenant_id=tenant_a, organization_id=org_a1.id)
    assert len(channel._subscriptions) == baseline_subscription_count
    filters_now = _live_exact_filters()
    assert any(f.tenant_id == tenant_a and f.organization_id == org_a1.id for f in filters_now)
    assert not any(f.tenant_id == tenant_b.id for f in filters_now)

    adapter.dispose()
    assert len(channel._subscriptions) == baseline_subscription_count - 1


def test_real_organization_switch_through_refresh_current_permissions_rewires_the_adapter(services):
    """True end-to-end proof through `PlatformWorkspaceCatalog.refreshCurrentPermissions()` (the
    real hook the QML shell calls after both a tenant and an organization switch)."""
    organization_service = services["organization_service"]
    catalog = _catalog(services)
    channel = services["platform_view_invalidation_channel"]
    adapter = catalog._approval_view_invalidation_adapter

    org_a1 = services["tenant_context_service"].get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique("VI-REALSWITCH-A2"), display_name="Real Switch Org A2", is_enabled=False
    )

    def _current_filters():
        return [filt for filt, _handler in channel._subscriptions.values() if isinstance(filt, ExactOrganization)]

    assert any(f.organization_id == org_a1.id for f in _current_filters())

    organization_service.enable_organization(org_a2.id)
    services["tenant_context_service"].set_active_organization(org_a2.id)
    catalog.refreshCurrentPermissions()

    filters_after_switch = _current_filters()
    assert any(f.organization_id == org_a2.id for f in filters_after_switch)
    assert not any(f.organization_id == org_a1.id for f in filters_after_switch)
    assert adapter is catalog._approval_view_invalidation_adapter


def test_adapter_follows_a_tenant_switch_via_refresh_current_permissions(services):
    catalog = _catalog(services)
    channel = services["platform_view_invalidation_channel"]
    tenant_a = _active_tenant(services)
    org_a1 = services["tenant_context_service"].get_active_organization()

    def _current_filters():
        return [filt for filt, _handler in channel._subscriptions.values() if isinstance(filt, ExactOrganization)]

    assert any(f.tenant_id == tenant_a and f.organization_id == org_a1.id for f in _current_filters())

    admin_svc = services["tenant_admin_service"]
    tenant_b = admin_svc.create_tenant(_unique("VI-TENANT-B"), "View Invalidation Tenant B")
    services["session"].flush()

    switch_result = catalog.tenantSwitcher.switchToTenant(tenant_b.id)
    assert switch_result["ok"] is True
    catalog.refreshCurrentPermissions()

    filters_after_switch = _current_filters()
    assert not any(f.tenant_id == tenant_a for f in filters_after_switch), (
        "the stale Tenant A/Org A1 subscription must be disposed after switching tenants"
    )


# ---------------------------------------------------------------------------
# Cross-org / cross-tenant UI isolation
# ---------------------------------------------------------------------------


def test_cross_org_decision_denial_produces_no_ui_refresh(services, session):
    """§35: Tenant A, active Org A1, Approval belongs to Org A2 -> zero refresh for A1's UI;
    after switching to A2, the identical decision succeeds and refreshes exactly once."""
    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh_approvals = lambda: refresh_calls.append("approvals") or None

    _login(services, "admin", "ChangeMe123!")
    organization_service = services["organization_service"]
    org_a1 = services["tenant_context_service"].get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique("VI-XORG-A2"), display_name="View Invalidation Cross-Org A2", is_enabled=False
    )
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    assert request.organization_id == org_a1.id

    approver_username = _unique("vi-xorg-approver")
    services["auth_service"].register_user(approver_username, "StrongPass123", role_names=["approver"])
    organization_service.enable_organization(org_a2.id)
    services["tenant_context_service"].set_active_organization(org_a2.id)
    catalog.refreshCurrentPermissions()
    refresh_calls.clear()

    _login(services, approver_username, "StrongPass123")
    approvals = services["approval_service"]
    with pytest.raises(NotFoundError):
        approvals.approve_and_apply(request.id)
    assert refresh_calls == []

    _login(services, "admin", "ChangeMe123!")
    organization_service.enable_organization(org_a1.id)
    services["tenant_context_service"].set_active_organization(org_a1.id)
    catalog.refreshCurrentPermissions()
    _login(services, approver_username, "StrongPass123")

    decided = approvals.approve_and_apply(request.id, note="Approved from the matching org")
    assert decided.status == ApprovalStatus.APPROVED
    assert refresh_calls == ["approvals"]


def test_cross_tenant_approval_event_produces_zero_callback(services, session):
    """§36: adapter scoped to Tenant A/Org A1 -- an event for a genuinely different tenant must
    never be observed, proven via two independent `TenantContextService` fakes over the same
    database (mirrors the Approval-P2 event-layer proof, extended here to the Qt adapter)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.core.platform.application.approval.approval_service import ApprovalService
    from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
    from src.core.platform.infrastructure.persistence.repositories.approval.approval import (
        SqlAlchemyApprovalRepository,
    )
    from src.core.platform.infrastructure.persistence.unit_of_work import (
        SqlAlchemyPlatformUnitOfWorkFactory,
    )
    from src.infra.events.in_process_post_commit_event_bus import InProcessPostCommitEventBus
    from src.infra.events.in_process_transactional_event_dispatcher import (
        InProcessTransactionalEventDispatcher,
    )
    from src.infra.persistence.orm.base import Base

    class _FixedClock:
        def now(self):
            from datetime import datetime, timezone

            return datetime(2031, 1, 1, tzinfo=timezone.utc)

    class _FakeTenantContextService:
        def __init__(self, tenant_id, organization_id):
            self._tenant_id = tenant_id
            self._organization_id = organization_id

        def require_active_scope_ids(self, *, operation_label):
            from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds

            return ActiveScopeIds(tenant_id=self._tenant_id, organization_id=self._organization_id)

        def require_active_organization_id(self, *, operation_label):
            return self._organization_id

        def require_active_tenant_id(self, *, operation_label):
            return self._tenant_id

        def get_active_tenant_id(self):
            return self._tenant_id

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    dispatcher = InProcessTransactionalEventDispatcher()
    bus = InProcessPostCommitEventBus()

    channel = services["platform_view_invalidation_channel"]
    factory_a = SqlAlchemyPlatformUnitOfWorkFactory(
        session_factory=session_factory, transactional_dispatcher=dispatcher, post_commit_bus=bus,
        tenant_context_service=_FakeTenantContextService("vi-xtenant-a", "vi-xorg-a"),
        user_session=None,
    )
    principal_a = UserSessionPrincipal(
        user_id="vi-xtenant-a-requester", username="vi-xtenant-a-requester", display_name="A Requester",
        role_names=frozenset(), permissions=frozenset(["approval.request"]),
    )
    session_a = UserSessionContext()
    session_a.set_principal(principal_a)
    approval_repo_a = SqlAlchemyApprovalRepository(session_factory())
    approval_repo_a._tenant_context_service = _FakeTenantContextService("vi-xtenant-a", "vi-xorg-a")
    approvals_a = ApprovalService(
        session=approval_repo_a.session, approval_repo=approval_repo_a, uow_factory=factory_a,
        user_session=session_a,
        tenant_context_service=_FakeTenantContextService("vi-xtenant-a", "vi-xorg-a"),
        clock=_FixedClock(),
    )

    # This mapper handler is bound to the app's REAL channel -- publishing through the
    # standalone factory above (a different bus) does not reach it at all, so subscribe a
    # handler on the same bus this standalone factory uses to prove the ADAPTER's exact-scope
    # filter is what matters, then verify the adapter (bound to the real app's channel) never
    # observes a hint published on a genuinely unrelated bus/tenant in the first place.
    mapper_handler = build_approval_view_invalidation_handler(channel)
    bus.subscribe(ApprovalRequested, mapper_handler)

    adapter = ApprovalViewInvalidationAdapter(
        channel=channel, tenant_id=_active_tenant(services),
        organization_id=services["tenant_context_service"].get_active_organization().id,
    )
    signal_calls = []
    adapter.approvalsStale.connect(lambda: signal_calls.append("stale"))

    approvals_a.request_change(
        request_type="baseline.create", entity_type="project_baseline",
        entity_id="cross-tenant-ui-probe", project_id=None, payload={"name": "Probe"},
    )

    assert signal_calls == []
    adapter.dispose()


# ---------------------------------------------------------------------------
# Failure suppression: apply/reject-handler, audit, commit, transactional/postcommit handler
# ---------------------------------------------------------------------------


def test_apply_handler_failure_produces_zero_ui_refresh(services, session):
    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh_approvals = lambda: refresh_calls.append("approvals") or None

    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    refresh_calls.clear()
    approvals = services["approval_service"]

    def _failing_handler(request, deps):
        raise RuntimeError("simulated apply participant failure")

    saved = approvals._apply_handlers["budget.approve"]
    approvals._apply_handlers["budget.approve"] = (_failing_handler, saved[1])
    try:
        with pytest.raises(RuntimeError):
            approvals.approve_and_apply(request.id)
    finally:
        approvals._apply_handlers["budget.approve"] = saved

    assert refresh_calls == []
    still_pending = [r for r in approvals.list_pending() if r.id == request.id]
    assert still_pending[0].status == ApprovalStatus.PENDING


def test_reject_handler_failure_produces_zero_ui_refresh(services, session):
    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh_approvals = lambda: refresh_calls.append("approvals") or None

    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    refresh_calls.clear()
    approvals = services["approval_service"]

    def _failing_reject_handler(request, deps):
        raise RuntimeError("simulated reject participant failure")

    saved = approvals._reject_handlers["budget.approve"]
    approvals._reject_handlers["budget.approve"] = (_failing_reject_handler, saved[1])
    try:
        with pytest.raises(RuntimeError):
            approvals.reject(request.id)
    finally:
        approvals._reject_handlers["budget.approve"] = saved

    assert refresh_calls == []


def test_audit_failure_produces_zero_ui_refresh(services):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh_approvals = lambda: refresh_calls.append("approvals") or None
    _login_as_fresh_requester(services)

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated audit failure")

    import pytest as _pytest

    monkeypatch = _pytest.MonkeyPatch()
    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    try:
        with pytest.raises(RuntimeError):
            services["approval_service"].request_change(
                request_type="baseline.create", entity_type="project_baseline",
                entity_id=_unique("audit-fail-ui-probe"), project_id=None,
                payload={"name": "Audit failure UI probe"},
            )
    finally:
        monkeypatch.undo()

    assert refresh_calls == []


def test_commit_failure_produces_zero_ui_refresh(services):
    from src.core.platform.infrastructure.persistence.unit_of_work import (
        SqlAlchemyPlatformUnitOfWork,
    )

    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh_approvals = lambda: refresh_calls.append("approvals") or None
    _login_as_fresh_requester(services)

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    import pytest as _pytest

    monkeypatch = _pytest.MonkeyPatch()
    monkeypatch.setattr(SqlAlchemyPlatformUnitOfWork, "commit", _fail_commit)
    try:
        with pytest.raises(RuntimeError):
            services["approval_service"].request_change(
                request_type="baseline.create", entity_type="project_baseline",
                entity_id=_unique("commit-fail-ui-probe"), project_id=None,
                payload={"name": "Commit failure UI probe"},
            )
    finally:
        monkeypatch.undo()

    assert refresh_calls == []


def test_transactional_handler_failure_rolls_back_with_zero_ui_refresh(services, monkeypatch):
    approvals = services["approval_service"]
    dispatcher = approvals._uow_factory._transactional_dispatcher
    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh_approvals = lambda: refresh_calls.append("approvals") or None
    _login_as_fresh_requester(services)

    def _failing_transactional_handler(event, uow):
        raise RuntimeError("simulated transactional handler failure")

    subscription = dispatcher.subscribe(ApprovalRequested, _failing_transactional_handler)
    try:
        with pytest.raises(RuntimeError):
            approvals.request_change(
                request_type="baseline.create", entity_type="project_baseline",
                entity_id=_unique("txn-fail-ui-probe"), project_id=None,
                payload={"name": "Transactional failure UI probe"},
            )
        assert refresh_calls == []
    finally:
        subscription.dispose()


def test_one_broken_postcommit_subscriber_does_not_block_the_control_workspace_refresh(services):
    """§26: ISOLATE_AND_CONTINUE -- a failing sibling postcommit subscriber must not prevent the
    Control workspace's own subscriber from firing, and the transaction stays committed."""
    channel = services["platform_view_invalidation_channel"]
    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh_approvals = lambda: refresh_calls.append("approvals") or None

    def _failing_subscriber(hint):
        raise RuntimeError("simulated broken subscriber")

    channel.subscribe(ExactOrganization(
        _active_tenant(services), services["tenant_context_service"].get_active_organization().id
    ), _failing_subscriber)
    _login_as_fresh_requester(services)

    request = services["approval_service"].request_change(
        request_type="baseline.create", entity_type="project_baseline",
        entity_id=_unique("postcommit-isolate-probe"), project_id=None,
        payload={"name": "Postcommit isolation probe"},
    )

    assert request.status == ApprovalStatus.PENDING
    assert refresh_calls == ["approvals"]
