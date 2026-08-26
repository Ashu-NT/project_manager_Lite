from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.security.authorization.roles.event_handlers.view_invalidation import (
    ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE,
    ROLE_BINDING_CATEGORY,
    build_role_binding_view_invalidation_handler,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.security.authorization.roles.events import (
    RoleBindingAssigned,
    RoleBindingRevoked,
)
from src.core.platform.domain.security.authorization.roles.role_binding_scope import (
    RoleBindingPlatformScope,
    RoleBindingResourceScope,
    RoleBindingTenantScope,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import ExactOrganization, OrganizationScope, PlatformScope, TenantScope, TenantWide
from src.core.platform.infrastructure.persistence.role_governance_unit_of_work import (
    SqlAlchemyRoleGovernanceUnitOfWork,
)
from src.ui_qml.platform.adapters.role_binding_view_invalidation_adapter import (
    RoleBindingViewInvalidationAdapter,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _active_tenant(services) -> str:
    return services["tenant_context_service"].get_active_tenant_id()


def _switch_session_to_actor(services, actor, *, tenant_id, organization_id=None, extra_permissions=()):
    auth = services["auth_service"]
    if organization_id is None:
        organization_id = services["tenant_context_service"].get_active_organization_id()
    principal = auth.build_principal_for_context(
        actor, tenant_id=tenant_id, organization_id=organization_id
    )
    services["user_session"].set_principal(
        replace(
            principal,
            session_id=None,
            permissions=frozenset({*principal.permissions, *extra_permissions}),
        )
    )


def _resource_scoped_binding_setup(services, *, suffix, scope_type, role_name, organization_id=None):
    auth = services["auth_service"]
    tenant_id = _active_tenant(services)
    actor = auth.register_user(
        _unique_code(f"p5c3-actor-{suffix}"), "P5C3Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code(f"p5c3-target-{suffix}"), "P5C3Target123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    target_role = auth._role_repo.get_by_name(role_name)
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id,
        assignable_role_id=target_role.id,
        target_scope_type=scope_type,
        tenant_id=tenant_id,
    )
    _switch_session_to_actor(
        services, actor, tenant_id=tenant_id, organization_id=organization_id,
        extra_permissions=("auth.role.assign",),
    )
    return target, target_role


# ---------------------------------------------------------------------------
# Mapper: both events -> the SAME target, scope-faithful (never collapsed to one shape)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("event_cls", [RoleBindingAssigned, RoleBindingRevoked])
def test_mapper_maps_tenant_scope_to_tenant_scope(event_cls):
    hints = []

    class _FakeChannel:
        def notify(self, hint):
            hints.append(hint)

    handler = build_role_binding_view_invalidation_handler(_FakeChannel())
    event = event_cls(
        binding_id="b-1", principal_id="p-1", role_id="r-1",
        scope=RoleBindingTenantScope(tenant_id="t-1"), occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="corr-1"))

    assert len(hints) == 1
    hint = hints[0]
    assert hint.scope == TenantScope("t-1")
    assert hint.category == ROLE_BINDING_CATEGORY
    assert hint.scope_code == ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE
    assert hint.entity_type == "role_binding"
    assert hint.entity_id == "b-1"


@pytest.mark.parametrize("event_cls", [RoleBindingAssigned, RoleBindingRevoked])
def test_mapper_maps_resource_scope_to_organization_scope_using_the_events_own_organization(event_cls):
    hints = []

    class _FakeChannel:
        def notify(self, hint):
            hints.append(hint)

    handler = build_role_binding_view_invalidation_handler(_FakeChannel())
    event = event_cls(
        binding_id="b-2", principal_id="p-2", role_id="r-2",
        scope=RoleBindingResourceScope(tenant_id="t-1", organization_id="o-1", scope_type="storeroom", scope_id="s-1"),
        occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="corr-2"))

    assert hints[0].scope == OrganizationScope("t-1", "o-1")


def test_mapper_maps_ownerless_resource_scope_to_tenant_scope_not_a_fabricated_organization():
    """A resource scope with `organization_id=None` (the resource genuinely has no owning
    organization -- e.g. a `Project` created with none) must map to `TenantScope`, never an
    invented `OrganizationScope` -- `organization_id=None` is never reinterpreted as
    "tenant-wide" via a flat/untyped field the way ADR-005 §12 explicitly warns against."""
    hints = []

    class _FakeChannel:
        def notify(self, hint):
            hints.append(hint)

    handler = build_role_binding_view_invalidation_handler(_FakeChannel())
    event = RoleBindingAssigned(
        binding_id="b-3", principal_id="p-3", role_id="r-3",
        scope=RoleBindingResourceScope(tenant_id="t-1", organization_id=None, scope_type="project", scope_id="proj-1"),
        occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="corr-3"))

    assert hints[0].scope == TenantScope("t-1")


def test_mapper_maps_platform_scope_to_platform_scope():
    hints = []

    class _FakeChannel:
        def notify(self, hint):
            hints.append(hint)

    handler = build_role_binding_view_invalidation_handler(_FakeChannel())
    event = RoleBindingAssigned(
        binding_id="b-4", principal_id="p-4", role_id="r-4",
        scope=RoleBindingPlatformScope(), occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="corr-4"))

    assert hints[0].scope == PlatformScope()


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


def test_role_binding_view_invalidation_mapper_has_no_qt_dependency():
    import src.core.platform.application.security.authorization.roles.event_handlers.view_invalidation as mapper_module

    imports = _imported_module_names(mapper_module)
    for forbidden in ("PySide6", "QtCore", "ui_qml", "domain_events"):
        assert not any(forbidden in name for name in imports), imports


# ---------------------------------------------------------------------------
# End-to-end: real canonical mutation -> real UI consumer refresh
# ---------------------------------------------------------------------------


def test_access_workspace_scope_grants_refresh_on_real_assign_mutation(services):
    catalog = _catalog(services)
    catalog.adminAccessWorkspace.refresh()
    site = services["site_service"].create_site(
        site_code=_unique_code("P5C3-SITE"), name="P5C-3 Site", city="Berlin", currency_code="EUR"
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=_unique_code("P5C3-ROOM"), name="P5C-3 Storeroom", site_id=site.id,
        status="ACTIVE", storeroom_type="MAIN",
    )
    catalog.adminAccessWorkspace.setScopeType("storeroom")
    catalog.adminAccessWorkspace.setScopeId(storeroom.id)
    assert catalog.adminAccessWorkspace.scopeGrants.get("items") == []

    user = services["auth_service"].register_user(
        _unique_code("p5c3-e2e-user"), "P5C3End2End123!", role_names=["inventory_manager"],
        tenant_id=_active_tenant(services),
    )
    services["access_service"].assign_scope_grant(
        scope_type="storeroom", scope_id=storeroom.id, user_id=user.id, scope_role="editor"
    )

    items = catalog.adminAccessWorkspace.scopeGrants.get("items")
    assert any(item.get("id") == user.id for item in items)


def test_access_workspace_full_catalog_options_do_not_needlessly_refresh(services):
    """P5C-3's main point: a RoleBinding transition must trigger ONLY the narrow
    `refresh_role_bindings()` reaction, never the coarse full `refresh()` -- proving
    `scope_type_options`/`user_options`/`role_options`/`scope_options` (none of which depend on
    RoleBinding state) are no longer needlessly reloaded."""
    catalog = _catalog(services)
    catalog.adminAccessWorkspace.refresh()
    full_refresh_calls = []
    catalog.adminAccessWorkspace.refresh = lambda: full_refresh_calls.append("refresh")
    site = services["site_service"].create_site(
        site_code=_unique_code("P5C3-NOFULL-SITE"), name="P5C-3 No-Full Site", city="Berlin", currency_code="EUR"
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=_unique_code("P5C3-NOFULL-ROOM"), name="P5C-3 No-Full Storeroom", site_id=site.id,
        status="ACTIVE", storeroom_type="MAIN",
    )
    user = services["auth_service"].register_user(
        _unique_code("p5c3-nofull-user"), "P5C3NoFull123!", role_names=["inventory_manager"],
        tenant_id=_active_tenant(services),
    )

    services["access_service"].assign_scope_grant(
        scope_type="storeroom", scope_id=storeroom.id, user_id=user.id, scope_role="editor"
    )

    assert full_refresh_calls == []


def test_no_refresh_before_commit_and_none_on_commit_failure(services, monkeypatch):
    catalog = _catalog(services)
    catalog.adminAccessWorkspace.refresh()
    refresh_calls = []
    catalog.adminAccessWorkspace.refresh_role_bindings = lambda: refresh_calls.append("refresh") or None
    site = services["site_service"].create_site(
        site_code=_unique_code("P5C3-COMMITFAIL-SITE"), name="Commit Fail Site", city="Berlin", currency_code="EUR"
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=_unique_code("P5C3-COMMITFAIL-ROOM"), name="Commit Fail Storeroom", site_id=site.id,
        status="ACTIVE", storeroom_type="MAIN",
    )
    user = services["auth_service"].register_user(
        _unique_code("p5c3-commitfail-user"), "P5C3CommitFail123!", role_names=["inventory_manager"],
        tenant_id=_active_tenant(services),
    )

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyRoleGovernanceUnitOfWork, "commit", _fail_commit)
    with pytest.raises(RuntimeError):
        services["access_service"].assign_scope_grant(
            scope_type="storeroom", scope_id=storeroom.id, user_id=user.id, scope_role="editor"
        )

    assert refresh_calls == []


def test_no_invalidation_on_no_op_assign_or_revoke(services):
    catalog = _catalog(services)
    catalog.adminAccessWorkspace.refresh()
    site = services["site_service"].create_site(
        site_code=_unique_code("P5C3-NOOP-SITE"), name="No-op Site", city="Berlin", currency_code="EUR"
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=_unique_code("P5C3-NOOP-ROOM"), name="No-op Storeroom", site_id=site.id,
        status="ACTIVE", storeroom_type="MAIN",
    )
    user = services["auth_service"].register_user(
        _unique_code("p5c3-noop-user"), "P5C3NoOp123!", role_names=["inventory_manager"],
        tenant_id=_active_tenant(services),
    )
    services["access_service"].assign_scope_grant(
        scope_type="storeroom", scope_id=storeroom.id, user_id=user.id, scope_role="editor"
    )
    refresh_calls = []
    catalog.adminAccessWorkspace.refresh_role_bindings = lambda: refresh_calls.append("refresh") or None

    # Identical already-active grant -- a true no-op per P5C-1/P5C-2's own established rule.
    services["access_service"].assign_scope_grant(
        scope_type="storeroom", scope_id=storeroom.id, user_id=user.id, scope_role="editor"
    )
    assert refresh_calls == []

    services["access_service"].remove_scope_grant(
        scope_type="storeroom", scope_id=storeroom.id, user_id=user.id
    )
    refresh_calls.clear()
    with pytest.raises(NotFoundError):
        services["access_service"].remove_scope_grant(
            scope_type="storeroom", scope_id=storeroom.id, user_id=user.id
        )
    assert refresh_calls == []


# ---------------------------------------------------------------------------
# Non-active organization / cross-tenant isolation
# ---------------------------------------------------------------------------


def test_non_active_organization_resource_mutation_does_not_refresh_the_active_orgs_ui(services):
    tenant_context_service = services["tenant_context_service"]
    catalog = _catalog(services)
    catalog.adminAccessWorkspace.refresh()
    org_a1_id = tenant_context_service.get_active_organization_id()
    site_a2_org = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C3-NONACTIVE-A2"), display_name="P5C-3 Non-Active A2", is_enabled=True
    )
    tenant_context_service.set_active_organization(site_a2_org.id)
    site_a2 = services["site_service"].create_site(
        site_code=_unique_code("P5C3-NONACTIVE-SITE"), name="A2 Site", city="Berlin", currency_code="EUR"
    )
    storeroom_a2 = services["inventory_service"].create_storeroom(
        storeroom_code=_unique_code("P5C3-NONACTIVE-ROOM"), name="A2 Storeroom", site_id=site_a2.id,
        status="ACTIVE", storeroom_type="MAIN",
    )
    services["organization_service"].update_organization(org_a1_id, is_enabled=True)
    tenant_context_service.set_active_organization(org_a1_id)
    assert tenant_context_service.get_active_organization_id() == org_a1_id

    refresh_calls = []
    catalog.adminAccessWorkspace.refresh_role_bindings = lambda: refresh_calls.append("refresh") or None
    user = services["auth_service"].register_user(
        _unique_code("p5c3-nonactive-user"), "P5C3NonActive123!", role_names=["inventory_manager"],
        tenant_id=_active_tenant(services),
    )

    # A1 remains active throughout -- the mutation targets an A2 storeroom without ever
    # switching. The A1-scoped adapter subscription must never fire.
    assert tenant_context_service.get_active_organization_id() == org_a1_id
    services["access_service"].assign_scope_grant(
        scope_type="storeroom", scope_id=storeroom_a2.id, user_id=user.id, scope_role="editor"
    )
    assert tenant_context_service.get_active_organization_id() == org_a1_id  # never switched

    assert refresh_calls == []


def test_switching_to_the_non_active_org_then_repeating_the_mutation_refreshes_exactly_once(services):
    tenant_context_service = services["tenant_context_service"]
    catalog = _catalog(services)
    catalog.adminAccessWorkspace.refresh()
    org_a1_id = tenant_context_service.get_active_organization_id()
    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C3-SWITCH-A2"), display_name="P5C-3 Switch A2", is_enabled=True
    )
    tenant_context_service.set_active_organization(org_a2.id)
    catalog.refreshCurrentPermissions()
    site_a2 = services["site_service"].create_site(
        site_code=_unique_code("P5C3-SWITCH-SITE"), name="Switch A2 Site", city="Berlin", currency_code="EUR"
    )
    storeroom_a2 = services["inventory_service"].create_storeroom(
        storeroom_code=_unique_code("P5C3-SWITCH-ROOM"), name="Switch A2 Storeroom", site_id=site_a2.id,
        status="ACTIVE", storeroom_type="MAIN",
    )
    user = services["auth_service"].register_user(
        _unique_code("p5c3-switch-user"), "P5C3Switch123!", role_names=["inventory_manager"],
        tenant_id=_active_tenant(services),
    )

    refresh_calls = []
    catalog.adminAccessWorkspace.refresh_role_bindings = lambda: refresh_calls.append("refresh") or None

    services["access_service"].assign_scope_grant(
        scope_type="storeroom", scope_id=storeroom_a2.id, user_id=user.id, scope_role="editor"
    )

    assert refresh_calls == ["refresh"]

    services["organization_service"].update_organization(org_a1_id, is_enabled=True)
    tenant_context_service.set_active_organization(org_a1_id)


def test_tenant_scope_mutation_refreshes_regardless_of_which_organization_is_active(services):
    """A tenant-scoped RoleBinding fact is organization-independent -- the `TenantWide`
    subscription must fire regardless of which organization happens to be active."""
    tenant_context_service = services["tenant_context_service"]
    catalog = _catalog(services)
    catalog.adminAccessWorkspace.refresh()
    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C3-TENANTSCOPE-A2"), display_name="P5C-3 Tenant Scope A2", is_enabled=True
    )
    tenant_context_service.set_active_organization(org_a2.id)
    catalog.refreshCurrentPermissions()

    refresh_calls = []
    catalog.adminAccessWorkspace.refresh_role_bindings = lambda: refresh_calls.append("refresh") or None
    auth = services["auth_service"]
    tenant_id = _active_tenant(services)
    actor = auth.register_user(
        _unique_code("p5c3-tenantscope-actor"), "P5C3TenantScope123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code("p5c3-tenantscope-target"), "P5C3TenantScope123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    viewer_role = auth._role_repo.get_by_name("viewer")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id, assignable_role_id=viewer_role.id,
        target_scope_type="tenant", tenant_id=tenant_id,
    )
    _switch_session_to_actor(services, actor, tenant_id=tenant_id, extra_permissions=("auth.role.assign",))

    services["role_governance_service"].assign_role(target_user_id=target.id, role_id=viewer_role.id)

    assert refresh_calls == ["refresh"]


def test_cross_tenant_mutation_attempt_produces_no_invalidation(services):
    from datetime import datetime as _dt

    from src.core.modules.inventory_procurement.infrastructure.persistence.orm.inventory import StoreroomORM
    from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM
    from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM
    from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import TenantORM

    channel = services["platform_view_invalidation_channel"]
    tenant_a = _active_tenant(services)
    session = services["session"]
    hints = []
    channel.subscribe(TenantWide(tenant_a), lambda hint: hints.append(hint))
    channel.subscribe(ExactOrganization(tenant_a, "does-not-matter"), lambda hint: hints.append(hint))

    now = _dt.now(timezone.utc)
    foreign_tenant_id = _unique_code("p5c3-foreign-tenant")
    session.add(TenantORM(id=foreign_tenant_id, tenant_code=_unique_code("P5C3FT"), display_name="Foreign Tenant", is_active=True, version=1))
    session.commit()
    foreign_org_id = _unique_code("p5c3-foreign-org")
    session.add(OrganizationORM(id=foreign_org_id, tenant_id=foreign_tenant_id, organization_code=_unique_code("P5C3FORG"), display_name="Foreign Org", is_active=True, version=1))
    session.commit()
    foreign_site_id = _unique_code("p5c3-foreign-site")
    session.add(SiteORM(id=foreign_site_id, tenant_id=foreign_tenant_id, organization_id=foreign_org_id, site_code=_unique_code("P5C3FSITE"), name="Foreign Site", is_active=True, created_at=now, updated_at=now, version=1))
    session.commit()
    foreign_storeroom_id = _unique_code("p5c3-foreign-storeroom")
    session.add(StoreroomORM(id=foreign_storeroom_id, tenant_id=foreign_tenant_id, organization_id=foreign_org_id, site_id=foreign_site_id, storeroom_code=_unique_code("P5C3FROOM"), name="Foreign Storeroom", status="ACTIVE", created_at=now, updated_at=now, version=1))
    session.commit()

    target, target_role = _resource_scoped_binding_setup(
        services, suffix="crosstenant", scope_type="storeroom", role_name="storeroom_viewer",
    )
    with pytest.raises(NotFoundError):
        services["role_governance_service"].assign_role(
            target_user_id=target.id, role_id=target_role.id, actual_scope_id=foreign_storeroom_id
        )

    assert hints == []


# ---------------------------------------------------------------------------
# Adapter: dual subscription shape, no AllTenants/AnyOrganizationInTenant
# ---------------------------------------------------------------------------


def test_adapter_subscribes_via_exact_organization_and_tenant_wide_only(services):
    from src.core.shared.events.view_invalidation import AllTenants, AnyOrganizationInTenant

    channel = services["platform_view_invalidation_channel"]
    tenant_id = _active_tenant(services)
    org = services["organization_service"].get_active_organization()

    adapter = RoleBindingViewInvalidationAdapter(channel=channel, tenant_id=tenant_id, organization_id=org.id)
    try:
        filters = [filt for filt, _handler in channel._subscriptions.values()]
        assert not any(isinstance(f, (AllTenants, AnyOrganizationInTenant)) for f in filters)
        assert any(isinstance(f, TenantWide) and f.tenant_id == tenant_id for f in filters)
        assert any(
            isinstance(f, ExactOrganization) and f.tenant_id == tenant_id and f.organization_id == org.id
            for f in filters
        )
    finally:
        adapter.dispose()


def test_adapter_only_reacts_to_its_exact_active_organization_for_resource_scope(services):
    channel = services["platform_view_invalidation_channel"]
    organization_service = services["organization_service"]
    tenant_id = _active_tenant(services)
    org_a1 = organization_service.get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique_code("P5C3-ADAPTER-A2"), display_name="Adapter Scope A2", is_enabled=False
    )

    adapter = RoleBindingViewInvalidationAdapter(channel=channel, tenant_id=tenant_id, organization_id=org_a1.id)
    signal_calls = []
    adapter.roleBindingsStale.connect(lambda: signal_calls.append("stale"))
    try:
        channel.notify(_hint(OrganizationScope(tenant_id, org_a2.id)))
        assert signal_calls == []

        channel.notify(_hint(OrganizationScope(tenant_id, org_a1.id)))
        assert signal_calls == ["stale"]
    finally:
        adapter.dispose()


def test_adapter_reacts_to_tenant_scope_regardless_of_active_organization(services):
    channel = services["platform_view_invalidation_channel"]
    tenant_id = _active_tenant(services)
    org = services["organization_service"].get_active_organization()

    adapter = RoleBindingViewInvalidationAdapter(channel=channel, tenant_id=tenant_id, organization_id=org.id)
    signal_calls = []
    adapter.roleBindingsStale.connect(lambda: signal_calls.append("stale"))
    try:
        channel.notify(_hint(TenantScope(tenant_id)))
        assert signal_calls == ["stale"]
    finally:
        adapter.dispose()


def _hint(scope):
    from src.core.shared.events.view_invalidation import ViewInvalidationHint

    return ViewInvalidationHint(
        scope=scope, category=ROLE_BINDING_CATEGORY, scope_code=ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE,
        entity_type="role_binding", entity_id="b-x",
    )


# ---------------------------------------------------------------------------
# Switch lifecycle
# ---------------------------------------------------------------------------


def test_real_organization_switch_through_refresh_current_permissions_rewires_the_adapter(services):
    organization_service = services["organization_service"]
    catalog = _catalog(services)
    channel = services["platform_view_invalidation_channel"]
    adapter = catalog._role_binding_view_invalidation_adapter

    org_a1 = organization_service.get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique_code("P5C3-REALSWITCH-A2"), display_name="Real Switch A2", is_enabled=False
    )

    def _exact_org_filters():
        return [f for f, _h in channel._subscriptions.values() if isinstance(f, ExactOrganization)]

    assert any(f.organization_id == org_a1.id for f in _exact_org_filters())

    organization_service.enable_organization(org_a2.id)
    tenant_context_service.set_active_organization(org_a2.id)
    catalog.refreshCurrentPermissions()

    filters_after = _exact_org_filters()
    assert any(f.organization_id == org_a2.id for f in filters_after)
    assert not any(f.organization_id == org_a1.id for f in filters_after)
    assert adapter is catalog._role_binding_view_invalidation_adapter


def test_adapter_follows_a_tenant_switch_via_refresh_current_permissions(services):
    catalog = _catalog(services)
    channel = services["platform_view_invalidation_channel"]
    tenant_a = _active_tenant(services)

    def _tenant_wide_filters():
        return [f for f, _h in channel._subscriptions.values() if isinstance(f, TenantWide)]

    assert any(f.tenant_id == tenant_a for f in _tenant_wide_filters())

    admin_svc = services["tenant_admin_service"]
    tenant_b = admin_svc.create_tenant(_unique_code("P5C3-TENANT-B"), "P5C-3 Tenant B")
    services["session"].flush()

    switch_result = catalog.tenantSwitcher.switchToTenant(tenant_b.id)
    assert switch_result["ok"] is True
    catalog.refreshCurrentPermissions()

    filters_after = _tenant_wide_filters()
    assert not any(f.tenant_id == tenant_a for f in filters_after), (
        "the stale Tenant A subscription must be disposed after switching tenants"
    )


def test_switching_does_not_accumulate_subscriptions(services):
    organization_service = services["organization_service"]
    catalog = _catalog(services)
    channel = services["platform_view_invalidation_channel"]
    org_a1 = organization_service.get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique_code("P5C3-NOACCUMULATE-A2"), display_name="No Accumulate A2", is_enabled=False
    )
    subscription_count_before = len(channel._subscriptions)

    organization_service.enable_organization(org_a2.id)
    tenant_context_service.set_active_organization(org_a2.id)
    catalog.refreshCurrentPermissions()
    organization_service.update_organization(org_a1.id, is_enabled=True)
    organization_service.enable_organization(org_a1.id)
    tenant_context_service.set_active_organization(org_a1.id)
    catalog.refreshCurrentPermissions()

    assert len(channel._subscriptions) == subscription_count_before


# ---------------------------------------------------------------------------
# Platform scope: denied, never fabricated
# ---------------------------------------------------------------------------


def test_platform_scope_assignment_remains_denied_no_invalidation_ever_fabricated(services):
    channel = services["platform_view_invalidation_channel"]
    from src.core.shared.events.view_invalidation import PlatformWide

    hints = []
    channel.subscribe(PlatformWide(), lambda hint: hints.append(hint))

    auth = services["auth_service"]
    tenant_id = _active_tenant(services)
    actor = auth.register_user(
        _unique_code("p5c3-platform-actor"), "P5C3Platform123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code("p5c3-platform-target"), "P5C3Platform123!", role_names=[], tenant_id=tenant_id
    )
    platform_role = auth._role_repo.get_by_name("admin")
    _switch_session_to_actor(services, actor, tenant_id=tenant_id, extra_permissions=("auth.role.assign",))

    with pytest.raises(BusinessRuleError):
        services["role_governance_service"].assign_role(target_user_id=target.id, role_id=platform_role.id)

    assert hints == []
