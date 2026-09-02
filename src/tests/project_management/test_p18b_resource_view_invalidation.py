"""P18B: Project Resource ViewInvalidation cutover + resources_changed retirement.

Covers: ResourceMasterChanged -> resource_list (OrganizationScope), ResourceCapabilityChanged ->
resource_capabilities (ResourceScope), scope isolation across organizations/resources, the real
Resources workspace controller's narrow reactions, the other 6 consumers' resourceListStale-only
wiring, the Employee-driven sync path producing exactly one Resource invalidation (no fake
cross-capability event, no duplicate), and the full retirement of `resources_changed` (zero
producers, zero consumers, field absent).
"""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.resources.event_handlers.view_invalidation import (
    RESOURCE_CAPABILITIES_SCOPE_CODE,
    RESOURCE_CATEGORY,
    RESOURCE_LIST_SCOPE_CODE,
)
from src.core.modules.project_management.domain.enums import WorkerType
from src.core.shared.events.view_invalidation import OrganizationScope, ResourceScope
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.adapters.resource_view_invalidation_adapter import (
    ResourceViewInvalidationAdapter,
)

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _pm_catalog(services) -> ProjectManagementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)


def _spy_hints(services):
    hints = []
    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )
    return hints


class _AnyOrgFilter:
    """Matches every hint regardless of scope kind -- for asserting on raw hint shape in tests
    that need to inspect `hint.scope` directly rather than filter by breadth."""

    def matches(self, scope) -> bool:
        return True


# ---------------------------------------------------------------------------
# DomainEvent -> ViewInvalidation mapping
# ---------------------------------------------------------------------------


def test_resource_master_changed_produces_resource_list_hint_at_organization_scope(services):
    hints = _spy_hints(services)
    org = services["tenant_context_service"].get_active_organization()

    resource = services["resource_service"].create_resource(name=_unique("MapMaster"))

    resource_hints = [h for h in hints if h.category == RESOURCE_CATEGORY]
    assert len(resource_hints) == 1
    hint = resource_hints[0]
    assert hint.scope_code == RESOURCE_LIST_SCOPE_CODE
    assert isinstance(hint.scope, OrganizationScope)
    assert hint.scope.tenant_id == org.tenant_id
    assert hint.scope.organization_id == org.id
    assert hint.entity_id == resource.id


def test_resource_capability_changed_produces_resource_capabilities_hint_at_resource_scope(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("MapCapability"))
    org = services["tenant_context_service"].get_active_organization()
    hints = _spy_hints(services)

    service.add_resource_skill(resource.id, "PY", "Python")

    resource_hints = [h for h in hints if h.category == RESOURCE_CATEGORY]
    assert len(resource_hints) == 1
    hint = resource_hints[0]
    assert hint.scope_code == RESOURCE_CAPABILITIES_SCOPE_CODE
    assert isinstance(hint.scope, ResourceScope)
    assert hint.scope.tenant_id == org.tenant_id
    assert hint.scope.organization_id == org.id
    assert hint.scope.module_code == "project_management"
    assert hint.scope.entity_type == "resource"
    assert hint.scope.entity_id == resource.id


def test_capability_change_never_produces_a_resource_list_hint(services):
    """List rows carry no skill/certification data (proven from source) -- a capability change
    must never trigger the list/options scope_code."""
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("NoListFromCap"))
    hints = _spy_hints(services)

    service.add_resource_skill(resource.id, "PY", "Python")

    assert not any(h.scope_code == RESOURCE_LIST_SCOPE_CODE for h in hints if h.category == RESOURCE_CATEGORY)


def test_master_change_never_produces_a_resource_capabilities_hint(services):
    hints = _spy_hints(services)

    services["resource_service"].create_resource(name=_unique("NoCapFromMaster"))

    assert not any(
        h.scope_code == RESOURCE_CAPABILITIES_SCOPE_CODE for h in hints if h.category == RESOURCE_CATEGORY
    )


def test_each_master_lifecycle_operation_produces_exactly_one_resource_list_hint(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("LifecycleHints"))

    for operation in (
        lambda: service.update_resource(
            resource_id=resource.id, expected_version=resource.version, name="Renamed",
            code=resource.code, kind=resource.kind, role="", hourly_rate=resource.hourly_rate,
            cost_type=resource.cost_type, currency_code=resource.currency_code,
            capacity_percent=resource.capacity_percent, address="", contact="",
            worker_type=resource.worker_type, employee_id=None, department_id=None, site_id=None,
        ),
    ):
        hints = _spy_hints(services)
        resource = operation()
        list_hints = [h for h in hints if h.category == RESOURCE_CATEGORY and h.scope_code == RESOURCE_LIST_SCOPE_CODE]
        assert len(list_hints) == 1


def test_no_op_update_produces_zero_hints(services):
    service = services["resource_service"]
    resource = service.create_resource(name=_unique("NoopHint"), role="Same")
    hints = _spy_hints(services)

    service.update_resource(
        resource_id=resource.id, expected_version=resource.version, name=resource.name,
        code=resource.code, kind=resource.kind, role=resource.role, hourly_rate=resource.hourly_rate,
        cost_type=resource.cost_type, currency_code=resource.currency_code,
        capacity_percent=resource.capacity_percent, address=resource.address, contact=resource.contact,
        worker_type=resource.worker_type, employee_id=None, department_id=None, site_id=None,
    )

    assert [h for h in hints if h.category == RESOURCE_CATEGORY] == []


def test_failed_mutation_produces_zero_hints(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService

    hints = _spy_hints(services)

    def _fail(self, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail)
    import pytest

    with pytest.raises(RuntimeError):
        services["resource_service"].create_resource(name=_unique("FailedHint"))
    monkeypatch.undo()

    assert [h for h in hints if h.category == RESOURCE_CATEGORY] == []


# ---------------------------------------------------------------------------
# P18B-FIX: dedupe by ViewInvalidation target/scope identity, not raw event fields
# ---------------------------------------------------------------------------


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def _master_event(*, tenant_id="t1", organization_id="o1", resource_id, version=1, change_type):
    from src.core.modules.project_management.application.resources.resource_master_events import (
        ResourceMasterChanged,
    )

    return ResourceMasterChanged(
        tenant_id=tenant_id, organization_id=organization_id, resource_id=resource_id,
        version=version, change_type=change_type,
    )


def _capability_event(*, tenant_id="t1", organization_id="o1", resource_id, child_id, child_version=1, change_type):
    from src.core.modules.project_management.application.resources.resource_capability_events import (
        ResourceCapabilityChanged,
    )

    return ResourceCapabilityChanged(
        tenant_id=tenant_id, organization_id=organization_id, resource_id=resource_id,
        child_id=child_id, child_version=child_version, child_type="ResourceSkill",
        change_type=change_type,
    )


def test_two_resources_same_org_same_transaction_produce_one_resource_list_hint():
    from src.core.modules.project_management.application.resources.event_handlers.view_invalidation import (
        build_resource_list_view_invalidation_handler,
    )
    from src.core.modules.project_management.application.resources.resource_master_events import (
        ResourceMasterChangeType,
    )
    from src.core.shared.events.domain_event_context import DomainEventContext

    channel = _fake_channel()
    handler = build_resource_list_view_invalidation_handler(channel)
    context = DomainEventContext(correlation_id="corr-1", causation_id=None)

    handler(
        _master_event(resource_id="res-a", change_type=ResourceMasterChangeType.CREATED), context
    )
    handler(
        _master_event(resource_id="res-b", change_type=ResourceMasterChangeType.CREATED), context
    )

    assert len(channel.notified) == 1


def test_two_resources_different_organizations_same_correlation_id_produce_two_resource_list_hints():
    """Structurally constructible even though a real single UoW transaction never spans two
    organizations -- the dedupe rule is by target/scope identity, and two different
    organizations are two different OrganizationScope targets regardless of correlation_id."""
    from src.core.modules.project_management.application.resources.event_handlers.view_invalidation import (
        build_resource_list_view_invalidation_handler,
    )
    from src.core.modules.project_management.application.resources.resource_master_events import (
        ResourceMasterChangeType,
    )
    from src.core.shared.events.domain_event_context import DomainEventContext

    channel = _fake_channel()
    handler = build_resource_list_view_invalidation_handler(channel)
    context = DomainEventContext(correlation_id="corr-1", causation_id=None)

    handler(
        _master_event(organization_id="org-a", resource_id="res-a", change_type=ResourceMasterChangeType.CREATED),
        context,
    )
    handler(
        _master_event(organization_id="org-b", resource_id="res-b", change_type=ResourceMasterChangeType.CREATED),
        context,
    )

    assert len(channel.notified) == 2
    assert {h.scope.organization_id for h in channel.notified} == {"org-a", "org-b"}


def test_same_resource_repeated_same_transaction_produces_one_capability_hint():
    from src.core.modules.project_management.application.resources.event_handlers.view_invalidation import (
        build_resource_capabilities_view_invalidation_handler,
    )
    from src.core.modules.project_management.application.resources.resource_capability_events import (
        ResourceCapabilityChangeType,
    )
    from src.core.shared.events.domain_event_context import DomainEventContext

    channel = _fake_channel()
    handler = build_resource_capabilities_view_invalidation_handler(channel)
    context = DomainEventContext(correlation_id="corr-1", causation_id=None)

    handler(
        _capability_event(resource_id="res-a", child_id="skill-1", change_type=ResourceCapabilityChangeType.ADDED),
        context,
    )
    handler(
        _capability_event(resource_id="res-a", child_id="skill-2", change_type=ResourceCapabilityChangeType.ADDED),
        context,
    )

    assert len(channel.notified) == 1


def test_two_resources_same_transaction_produce_two_capability_hints():
    from src.core.modules.project_management.application.resources.event_handlers.view_invalidation import (
        build_resource_capabilities_view_invalidation_handler,
    )
    from src.core.modules.project_management.application.resources.resource_capability_events import (
        ResourceCapabilityChangeType,
    )
    from src.core.shared.events.domain_event_context import DomainEventContext

    channel = _fake_channel()
    handler = build_resource_capabilities_view_invalidation_handler(channel)
    context = DomainEventContext(correlation_id="corr-1", causation_id=None)

    handler(
        _capability_event(resource_id="res-a", child_id="skill-1", change_type=ResourceCapabilityChangeType.ADDED),
        context,
    )
    handler(
        _capability_event(resource_id="res-b", child_id="skill-2", change_type=ResourceCapabilityChangeType.ADDED),
        context,
    )

    assert len(channel.notified) == 2
    assert {h.entity_id for h in channel.notified} == {"res-a", "res-b"}


def test_same_resource_list_target_across_two_transactions_produces_two_hints(services):
    """Dedupe is transaction-scoped only -- a second, later, genuinely separate transaction
    targeting the same organization must never be silently suppressed by the first."""
    service = services["resource_service"]
    hints = _spy_hints(services)

    service.create_resource(name=_unique("XactA"))
    service.create_resource(name=_unique("XactB"))

    list_hints = [h for h in hints if h.category == RESOURCE_CATEGORY and h.scope_code == RESOURCE_LIST_SCOPE_CODE]
    assert len(list_hints) == 2


# ---------------------------------------------------------------------------
# Scope isolation
# ---------------------------------------------------------------------------


def test_org_a_resource_event_does_not_reach_org_b_subscriber(services):
    org_a = services["tenant_context_service"].get_active_organization()
    adapter_b_calls = []
    adapter = ResourceViewInvalidationAdapter(
        channel=services["platform_view_invalidation_channel"],
        tenant_id=org_a.tenant_id,
        organization_id="org-b-does-not-exist",
    )
    adapter.resourceListStale.connect(lambda rid: adapter_b_calls.append(rid))

    services["resource_service"].create_resource(name=_unique("OrgIsolation"))

    assert adapter_b_calls == []


def test_resource_a_capability_event_does_not_reach_consumer_filtering_for_resource_b(services):
    service = services["resource_service"]
    resource_a = service.create_resource(name=_unique("ResA"))
    resource_b = service.create_resource(name=_unique("ResB"))
    org = services["tenant_context_service"].get_active_organization()

    reactions_for_b = []
    adapter = ResourceViewInvalidationAdapter(
        channel=services["platform_view_invalidation_channel"],
        tenant_id=org.tenant_id,
        organization_id=org.id,
    )
    adapter.resourceCapabilitiesStale.connect(
        lambda rid: reactions_for_b.append(rid) if rid == resource_b.id else None
    )

    service.add_resource_skill(resource_a.id, "PY", "Python")

    assert reactions_for_b == []


def test_exact_organization_filter_matches_resource_scope(services):
    """P16D-FIX's ExactOrganization/ResourceScope matching extension applies here too --
    ResourceScope is a strict refinement of OrganizationScope."""
    from src.core.shared.events.view_invalidation import ExactOrganization

    org = services["tenant_context_service"].get_active_organization()
    filt = ExactOrganization(org.tenant_id, org.id)
    scope = ResourceScope(
        tenant_id=org.tenant_id, organization_id=org.id,
        module_code="project_management", entity_type="resource", entity_id="any-resource",
    )
    assert filt.matches(scope) is True


# ---------------------------------------------------------------------------
# Resources workspace controller: narrow reactions
# ---------------------------------------------------------------------------


def test_resources_workspace_refreshes_on_any_master_change(services):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.resourcesWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    services["resource_service"].create_resource(name=_unique("WorkspaceMaster"))

    assert refresh_calls == ["refresh"]


def test_resources_workspace_does_not_refresh_on_unrelated_resource_capability_change(services):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.resourcesWorkspace
    other_resource = services["resource_service"].create_resource(name=_unique("Other"))
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    services["resource_service"].add_resource_skill(other_resource.id, "PY", "Python")

    assert refresh_calls == []


def test_resources_workspace_reloads_capabilities_only_for_selected_resource(services):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.resourcesWorkspace
    resource = services["resource_service"].create_resource(name=_unique("SelectedCap"))
    other_resource = services["resource_service"].create_resource(name=_unique("OtherCap"))
    controller._selected_resource_id = resource.id

    reload_calls = []
    import src.ui_qml.modules.project_management.controllers.resources.resource_domain_event_binder as binder_module
    original = binder_module.reload_skills_and_certs
    binder_module.reload_skills_and_certs = lambda ctrl, rid: reload_calls.append(rid)
    try:
        services["resource_service"].add_resource_skill(other_resource.id, "PY", "Python")
        assert reload_calls == []

        services["resource_service"].add_resource_skill(resource.id, "JS", "JavaScript")
        assert reload_calls == [resource.id]
    finally:
        binder_module.reload_skills_and_certs = original


# ---------------------------------------------------------------------------
# Other consumers: resourceListStale only (no resourceCapabilitiesStale wiring)
# ---------------------------------------------------------------------------


def test_dashboard_portfolio_scheduling_tasks_timesheets_refresh_on_master_change_only(services, qapp):
    """These 6 consumers react via `_request_domain_refresh()`'s existing QTimer-coalesced
    scheduling (unchanged by P18B), so a real refresh only lands after the Qt event loop runs
    once -- `qapp.processEvents()` mirrors the same pattern already used for e.g. Portfolio in
    test_qml_domain_event_bridges_pm.py."""
    from PySide6.QtWidgets import QApplication

    pm_catalog = _pm_catalog(services)
    controllers = {
        "dashboard": pm_catalog.dashboardWorkspace,
        "portfolio": pm_catalog.portfolioWorkspace,
        "scheduling": pm_catalog.schedulingWorkspace,
        "tasks": pm_catalog.tasksWorkspace,
        "timesheets": pm_catalog.timesheetsWorkspace,
        "reviewQueue": pm_catalog.reviewQueueWorkspace,
    }
    controllers["dashboard"].load()  # dashboard ignores domain refresh until _has_loaded
    refresh_calls = {name: [] for name in controllers}
    for name, controller in controllers.items():
        controller.refresh = (lambda n: lambda: refresh_calls[n].append("refresh"))(name)

    services["resource_service"].create_resource(name=_unique("SharedMasterRefresh"))
    QApplication.processEvents()

    for name in controllers:
        assert refresh_calls[name] == ["refresh"], f"{name} did not react to resource_list"


def test_dashboard_portfolio_scheduling_tasks_timesheets_do_not_refresh_on_capability_change(services, qapp):
    from PySide6.QtWidgets import QApplication

    pm_catalog = _pm_catalog(services)
    resource = services["resource_service"].create_resource(name=_unique("NoCapRefresh"))
    controllers = {
        "dashboard": pm_catalog.dashboardWorkspace,
        "portfolio": pm_catalog.portfolioWorkspace,
        "scheduling": pm_catalog.schedulingWorkspace,
        "tasks": pm_catalog.tasksWorkspace,
        "timesheets": pm_catalog.timesheetsWorkspace,
        "reviewQueue": pm_catalog.reviewQueueWorkspace,
    }
    refresh_calls = {name: [] for name in controllers}
    for name, controller in controllers.items():
        controller.refresh = (lambda n: lambda: refresh_calls[n].append("refresh"))(name)

    services["resource_service"].add_resource_skill(resource.id, "PY", "Python")
    QApplication.processEvents()

    for name in controllers:
        assert refresh_calls[name] == [], f"{name} incorrectly reacted to resource_capabilities"


def test_control_workspace_no_longer_reacts_to_resource_events(services):
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.controlWorkspace
    controller.ensureLoaded()
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    services["resource_service"].create_resource(name=_unique("ControlNoReact"))

    assert refresh_calls == []


# ---------------------------------------------------------------------------
# Employee integration (P18B §20)
# ---------------------------------------------------------------------------


def test_employee_update_produces_exactly_one_resource_list_hint_when_resource_linked(services):
    employee_service = services["employee_service"]
    resource_service = services["resource_service"]
    employee = employee_service.create_employee(
        employee_code=_unique("EMP"), full_name="Original Name", title="Engineer"
    )
    resource = resource_service.create_resource(
        name="placeholder", worker_type=WorkerType.EMPLOYEE, employee_id=employee.id
    )
    hints = _spy_hints(services)

    employee_service.update_employee(employee.id, full_name="Updated Name")

    resource_hints = [h for h in hints if h.category == RESOURCE_CATEGORY]
    assert len(resource_hints) == 1
    assert resource_hints[0].scope_code == RESOURCE_LIST_SCOPE_CODE
    assert resource_hints[0].entity_id == resource.id


def test_employee_update_with_no_linked_resource_produces_zero_resource_hints(services):
    employee_service = services["employee_service"]
    employee = employee_service.create_employee(
        employee_code=_unique("EMP"), full_name="No Resource"
    )
    hints = _spy_hints(services)

    employee_service.update_employee(employee.id, full_name="No Resource 2")

    assert [h for h in hints if h.category == RESOURCE_CATEGORY] == []


def test_resources_workspace_refreshes_once_from_employee_driven_resource_sync(services):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.resourcesWorkspace
    employee_service = services["employee_service"]
    resource_service = services["resource_service"]
    employee = employee_service.create_employee(
        employee_code=_unique("EMP"), full_name="Sync Name", title="Engineer"
    )
    resource_service.create_resource(
        name="placeholder", worker_type=WorkerType.EMPLOYEE, employee_id=employee.id
    )
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    employee_service.update_employee(employee.id, full_name="Synced Name")

    assert refresh_calls == ["refresh"]  # exactly one -- no duplicate from a second path


# ---------------------------------------------------------------------------
# Architecture guards: resources_changed fully retired
# ---------------------------------------------------------------------------


def test_resources_changed_field_is_absent_from_domain_events():
    from src.core.shared.events.domain_events import domain_events

    assert not hasattr(domain_events, "resources_changed")


def test_resources_changed_has_zero_production_references():
    """Checks for actual usage (`domain_events.resources_changed`), not the bare substring --
    several files carry deliberate retirement comments explaining the P18B removal (matching
    this session's established convention, e.g. P16C's "superseded" comments), which would
    otherwise false-positive a blanket substring scan."""
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "domain_events.resources_changed" in source or "resources_changed:" in source:
            hits.append(normalized)
    assert hits == [], hits


def test_ui_never_subscribes_directly_to_raw_resource_domain_events():
    """Production UI path must stay DomainEvent -> postcommit handler -> ViewInvalidationHint ->
    channel -> scoped adapter -> narrow refresh; no QML/controller code may import or subscribe
    to ResourceMasterChanged/ResourceCapabilityChanged directly."""
    import glob

    hits = []
    for path in glob.glob("src/ui_qml/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "ResourceMasterChanged" in source or "ResourceCapabilityChanged" in source:
            hits.append(normalized)
    assert hits == [], hits


def test_no_generic_bridge_or_service_locator_introduced():
    import inspect

    from src.core.modules.project_management.application.resources.event_handlers import (
        view_invalidation as handler_module,
    )

    source = inspect.getsource(handler_module)
    for forbidden in ("repository_for(", "resolve(", "repositories[", "container.get("):
        assert forbidden not in source
