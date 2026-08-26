from __future__ import annotations

import pytest

from src.core.platform.access.authorization import require_scope_permission
from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.modules.inventory_procurement.access.policy import resolve_storeroom_scope_permissions
from src.core.modules.project_management.access.policy import resolve_project_scope_permissions
from src.core.platform.domain.master_data.site.access_policy import resolve_site_scope_permissions
from src.tests.ui_runtime_helpers import login_as


def _register_active_tenant_user(
    services,
    username: str,
    *,
    role_names: list[str],
):
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="prepare scoped-access test user"
    )
    return services["auth_service"].register_user(
        username,
        "StrongPass123",
        role_names=role_names,
        tenant_id=tenant_id,
    )


def test_user_session_supports_generic_scoped_access_and_project_compatibility():
    user_session = UserSessionContext()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="user-1",
            username="scoped-user",
            display_name=None,
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"task.read", "inventory.read"}),
            scoped_access={
                "project": {"project-1": frozenset({"task.read"})},
                "storeroom": {"storeroom-1": frozenset({"inventory.read"})},
            },
        )
    )

    assert user_session.has_scope_permission("project", "project-1", "task.read") is True
    assert user_session.has_project_permission("project-1", "task.read") is True
    assert user_session.has_scope_permission("project", "project-2", "task.read") is False
    assert user_session.has_scope_permission("storeroom", "storeroom-1", "inventory.read") is True
    assert user_session.has_any_scope_access("storeroom", "inventory.read") is True
    assert user_session.scope_ids_for("storeroom", "inventory.read") == {"storeroom-1"}
    assert user_session.is_scope_restricted("project") is True
    assert user_session.is_project_restricted() is True
    assert user_session.principal is not None
    assert user_session.principal.project_access == {"project-1": frozenset({"task.read"})}


def test_require_scope_permission_uses_generic_scope_model():
    user_session = UserSessionContext()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="user-2",
            username="project-reader",
            display_name=None,
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"task.read"}),
            scoped_access={"project": {"project-1": frozenset({"task.read"})}},
        )
    )

    require_scope_permission(
        user_session,
        "project",
        "project-1",
        "task.read",
        operation_label="view project tasks",
    )

    with pytest.raises(BusinessRuleError, match="project 'project-2'"):
        require_scope_permission(
            user_session,
            "project",
            "project-2",
            "task.read",
            operation_label="view project tasks",
        )


def test_access_service_no_longer_supports_organization_scope(services):
    target = _register_active_tenant_user(
        services,
        "retired-org-scope-target",
        role_names=["viewer"],
    )

    with pytest.raises(ValidationError) as exc_info:
        services["access_service"].assign_scope_grant(
            scope_type="organization",
            scope_id="anything",
            user_id=target.id,
            scope_role="viewer",
        )

    assert exc_info.value.code == "UNSUPPORTED_SCOPE_TYPE"


def test_access_service_rejects_target_from_another_tenant(services):
    project = services["project_service"].create_project(
        "Cross Tenant Access Target"
    )
    other_tenant = services["tenant_admin_service"].create_tenant(
        "ACCESS-TARGET",
        "Access Target Tenant",
    )
    target = services["auth_service"].register_user(
        "cross-tenant-membership-target",
        "StrongPass123",
        role_names=["viewer"],
        tenant_id=other_tenant.id,
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        services["access_service"].assign_scope_grant(
            scope_type="project",
            scope_id=project.id,
            user_id=target.id,
            scope_role="viewer",
        )

    assert exc_info.value.code == "ACCESS_TARGET_TENANT_DENIED"


def test_auth_build_principal_populates_generic_scoped_access_from_project_memberships(services):
    auth = services["auth_service"]
    access = services["access_service"]
    project = services["project_service"].create_project("Scoped Principal Project")
    user = _register_active_tenant_user(
        services,
        "scoped-principal-user",
        role_names=["viewer"],
    )

    access.assign_scope_grant(
        scope_type="project",
        scope_id=project.id,
        user_id=user.id,
        scope_role="viewer",
    )

    principal = auth.build_principal(user)

    assert principal.scoped_access["project"][project.id] == frozenset(
        resolve_project_scope_permissions("viewer")
    )
    assert principal.project_access[project.id] == principal.scoped_access["project"][project.id]


def test_access_service_supports_storeroom_scope_grants_and_principal_hydration(services):
    auth = services["auth_service"]
    access = services["access_service"]
    site = services["site_service"].create_site(
        site_code="STR-ACC",
        name="Scoped Access Site",
        city="Berlin",
        currency_code="EUR",
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="STR-ACCESS",
        name="Scoped Access Storeroom",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    user = _register_active_tenant_user(
        services,
        "storeroom-scope-user",
        role_names=["inventory_manager"],
    )

    grant = access.assign_scope_grant(
        scope_type="storeroom",
        scope_id=storeroom.id,
        user_id=user.id,
        scope_role="editor",
    )

    assert grant.scope_type == "storeroom"
    assert grant.scope_id == storeroom.id
    assert grant.scope_role == "operator"
    assert grant.permission_codes == sorted(resolve_storeroom_scope_permissions("operator"))
    assert access.list_scope_role_choices("storeroom") == ("viewer", "operator", "manager")
    assert set(access.list_supported_scope_types()) == {
        "project",
        "site",
        "storeroom",
    }

    listed_scope_grants = access.list_scope_grants("storeroom", storeroom.id)
    listed_user_grants = access.list_user_scope_grants(user.id, scope_type="storeroom")
    principal = auth.build_principal(user)

    assert len(listed_scope_grants) == 1
    assert len(listed_user_grants) == 1
    assert listed_scope_grants[0].id == grant.id
    assert listed_user_grants[0].id == grant.id
    assert principal.scoped_access["storeroom"][storeroom.id] == frozenset(
        resolve_storeroom_scope_permissions("operator")
    )


def test_storeroom_scope_grant_targets_a_non_active_organization(services):
    """P5C prerequisite: confirmed ambient-scope bug (the same class of defect already fixed for
    Organization in P4B and Module Entitlements in the P5B prerequisite pass) -- the storeroom
    `scope_exists_resolver` used to compare `storeroom.organization_id` against the CURRENTLY
    ACTIVE organization, making it structurally impossible to grant/revoke storeroom-scoped
    access (or assign a canonical role at storeroom scope) for a storeroom belonging to any
    non-active organization within the caller's own tenant. Mandatory scenario: active org A1,
    grant/revoke targets a storeroom that belongs to org A2 -- must succeed, and must not affect
    or require switching the active organization.

    P5C-1 CORRECTION (reopened finding): this test originally only flipped `Organization
    .is_active` in the DB via `create_organization(is_enabled=True)` -- a completely different
    mechanism from the SESSION-level active organization
    (`tenant_context_service`/`user_session.active_organization_id()`) that
    `require_active_scope_ids()` (and therefore every ambient-org-scoped repository read)
    actually consults. Flipping only the DB flag never moved the ambient session org away from
    A1, so this test was a false negative: it asserted `organization_service
    .get_active_organization().id == org_a2.id` (the DB flag, an unrelated read) and never
    proved anything about the repository-scoping mechanism the bug lived in. Fixed here by
    explicitly calling `tenant_context_service.set_active_organization(...)` -- the actual
    ambient switch -- and asserting against THAT, not the DB flag. The underlying resolver
    (`_storeroom_exists`/`_storeroom_exists_for_role_governance` in `inventory_registry.py`) is
    now genuinely fixed via `StoreroomRepository.get_for_tenant()` (tenant-scoped only, added in
    P5C-1), which this corrected test actually exercises."""
    access = services["access_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a1 = organization_service.get_active_organization()
    site_a1 = services["site_service"].create_site(
        site_code="STR-A1-SITE",
        name="Org A1 Site",
        city="Berlin",
        currency_code="EUR",
    )
    storeroom_a1 = services["inventory_service"].create_storeroom(
        storeroom_code="STR-A1-ROOM",
        name="Org A1 Storeroom",
        site_id=site_a1.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    assert storeroom_a1.organization_id == org_a1.id

    org_a2 = organization_service.create_organization(
        organization_code="STR-SCOPE-A2", display_name="Storeroom Scope Org A2", is_enabled=True
    )
    # The actual ambient SESSION-level switch -- what `require_active_scope_ids()` reads, and
    # therefore what `StoreroomRepository.get()`'s (now bypassed) active-org filter keys off.
    # Deliberately NOT relying on the DB `is_active` flag flip alone (the original false
    # negative): `set_active_organization` happens to also require the target's own
    # `is_active` flag, but that flag is unrelated to -- and, per this fix, no longer consulted
    # by -- the storeroom resolver's own organization-ownership check.
    tenant_context_service.set_active_organization(org_a2.id)
    assert tenant_context_service.get_active_organization_id() == org_a2.id

    user = _register_active_tenant_user(
        services,
        "storeroom-nonactive-org-user",
        role_names=["inventory_manager"],
    )

    # Active organization is now A2, but the storeroom being granted belongs to A1 -- must
    # succeed without switching back.
    grant = access.assign_scope_grant(
        scope_type="storeroom",
        scope_id=storeroom_a1.id,
        user_id=user.id,
        scope_role="editor",
    )
    assert tenant_context_service.get_active_organization_id() == org_a2.id  # never switched
    assert grant.scope_id == storeroom_a1.id

    access.remove_scope_grant(
        scope_type="storeroom",
        scope_id=storeroom_a1.id,
        user_id=user.id,
    )
    assert tenant_context_service.get_active_organization_id() == org_a2.id  # still never switched
    assert access.list_scope_grants("storeroom", storeroom_a1.id) == []


def test_storeroom_scope_grant_targets_the_active_organization_while_a_different_org_is_current_target(
    services,
):
    """Inverse of the non-active-organization scenario: active org A1, storeroom belongs to A2
    (created but never made ambiently active) -- must equally succeed. Proves the fix is
    symmetric, not merely "the specific direction the regression happened to exercise"."""
    access = services["access_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a1_id = tenant_context_service.get_active_organization_id()
    org_a2 = organization_service.create_organization(
        organization_code="STR-SCOPE-INV-A2", display_name="Storeroom Scope Inverse Org A2", is_enabled=True
    )
    # Creating A2 as `is_active=True` deactivates A1's own DB flag as a side effect (a separate,
    # unrelated mechanism from the ambient session org this test manipulates directly).

    # Build a site/storeroom under A2 by switching the ambient session org to it temporarily --
    # this setup step, unlike the actual grant below, is allowed to switch. A2 is already the
    # DB-active organization at this point, so the switch succeeds.
    tenant_context_service.set_active_organization(org_a2.id)
    site_a2 = services["site_service"].create_site(
        site_code="STR-A2-SITE", name="Org A2 Site", city="Berlin", currency_code="EUR"
    )
    storeroom_a2 = services["inventory_service"].create_storeroom(
        storeroom_code="STR-A2-ROOM", name="Org A2 Storeroom", site_id=site_a2.id,
        status="ACTIVE", storeroom_type="MAIN",
    )
    assert storeroom_a2.organization_id == org_a2.id

    # Reactivate A1 (deactivating A2 in turn -- fine, A2 has already served its purpose as the
    # ambient org for setup) so the switch back to A1 succeeds.
    organization_service.update_organization(org_a1_id, is_enabled=True)
    tenant_context_service.set_active_organization(org_a1_id)
    assert tenant_context_service.get_active_organization_id() == org_a1_id

    user = _register_active_tenant_user(
        services,
        "storeroom-inverse-nonactive-org-user",
        role_names=["inventory_manager"],
    )

    grant = access.assign_scope_grant(
        scope_type="storeroom", scope_id=storeroom_a2.id, user_id=user.id, scope_role="editor"
    )
    assert tenant_context_service.get_active_organization_id() == org_a1_id  # never switched
    assert grant.scope_id == storeroom_a2.id


def test_access_service_supports_site_scope_grants_and_site_filtering(services):
    auth = services["auth_service"]
    access = services["access_service"]
    site_a = services["site_service"].create_site(
        site_code="SITE-A",
        name="Allowed Site",
        city="Berlin",
        currency_code="EUR",
    )
    services["site_service"].create_site(
        site_code="SITE-B",
        name="Blocked Site",
        city="Munich",
        currency_code="EUR",
    )
    user = _register_active_tenant_user(
        services,
        "site-scope-user",
        role_names=["inventory_manager"],
    )

    grant = access.assign_scope_grant(
        scope_type="site",
        scope_id=site_a.id,
        user_id=user.id,
        scope_role="manager",
    )

    assert grant.permission_codes == sorted(resolve_site_scope_permissions("manager"))
    principal = auth.build_principal(user)
    assert principal.scoped_access["site"][site_a.id] == frozenset(resolve_site_scope_permissions("manager"))

    login_as(services, "site-scope-user", "StrongPass123")
    visible_sites = services["site_service"].list_sites()

    assert [site.id for site in visible_sites] == [site_a.id]


def test_storeroom_scoped_access_filters_inventory_and_stock_queries(services):
    auth = services["auth_service"]
    access = services["access_service"]
    site = services["site_service"].create_site(
        site_code="STR-FLT",
        name="Filtered Site",
        city="Hamburg",
        currency_code="EUR",
    )
    accessible = services["inventory_service"].create_storeroom(
        storeroom_code="FLT-A",
        name="Accessible Storeroom",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    blocked = services["inventory_service"].create_storeroom(
        storeroom_code="FLT-B",
        name="Blocked Storeroom",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    item = services["inventory_item_service"].create_item(
        item_code="FLT-ITEM",
        name="Scoped Filter Item",
        status="ACTIVE",
        stock_uom="EA",
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=accessible.id,
        quantity=10,
        unit_cost=2.0,
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=blocked.id,
        quantity=5,
        unit_cost=3.0,
    )
    user = _register_active_tenant_user(
        services,
        "storeroom-filter-user",
        role_names=["inventory_manager"],
    )
    access.assign_scope_grant(
        scope_type="storeroom",
        scope_id=accessible.id,
        user_id=user.id,
        scope_role="manager",
    )

    login_as(services, "storeroom-filter-user", "StrongPass123")

    storerooms = services["inventory_service"].list_storerooms()
    balances = services["inventory_stock_service"].list_balances()
    transactions = services["inventory_stock_service"].list_transactions()

    assert [row.id for row in storerooms] == [accessible.id]
    assert {(row.stock_item_id, row.storeroom_id) for row in balances} == {(item.id, accessible.id)}
    assert {row.storeroom_id for row in transactions} == {accessible.id}

    with pytest.raises(BusinessRuleError, match="storeroom"):
        services["inventory_service"].get_storeroom(blocked.id)

    with pytest.raises(BusinessRuleError, match="storeroom"):
        services["inventory_stock_service"].get_balance_for_stock_position(
            stock_item_id=item.id,
            storeroom_id=blocked.id,
        )

