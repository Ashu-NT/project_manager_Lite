from __future__ import annotations

import pytest

from core.platform.access.authorization import require_scope_permission
from core.platform.auth.session import UserSessionContext, UserSessionPrincipal
from core.platform.common.exceptions import BusinessRuleError
from core.modules.inventory_procurement.access.policy import resolve_storeroom_scope_permissions
from core.modules.project_management.access.policy import resolve_project_scope_permissions
from core.platform.org.access_policy import resolve_site_scope_permissions
from tests.ui_runtime_helpers import login_as


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


def test_auth_build_principal_populates_generic_scoped_access_from_project_memberships(services):
    auth = services["auth_service"]
    access = services["access_service"]
    project = services["project_service"].create_project("Scoped Principal Project")
    user = auth.register_user("scoped-principal-user", "StrongPass123", role_names=["viewer"])

    access.assign_project_membership(
        project_id=project.id,
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
    user = auth.register_user("storeroom-scope-user", "StrongPass123", role_names=["inventory_manager"])

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
    assert access.list_supported_scope_types() == ("project", "site", "storeroom")

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
    user = auth.register_user("site-scope-user", "StrongPass123", role_names=["inventory_manager"])

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
    user = auth.register_user("storeroom-filter-user", "StrongPass123", role_names=["inventory_manager"])
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
