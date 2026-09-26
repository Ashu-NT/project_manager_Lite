from __future__ import annotations

from src.core.platform.application.platform_runtime.module_access_policy import (
    is_module_accessible,
)
from src.core.platform.domain.security.auth.session import UserSessionPrincipal


def test_is_module_accessible_true_when_a_registered_prefix_permission_is_held():
    assert is_module_accessible("project_management", frozenset({"task.read"})) is True


def test_is_module_accessible_false_when_no_relevant_permission_is_held():
    assert is_module_accessible("project_management", frozenset({"settings.manage"})) is False


def test_is_module_accessible_false_for_an_unregistered_module_code():
    assert is_module_accessible("payroll", frozenset({"settings.manage"})) is False


def test_is_module_accessible_false_for_platform_which_is_not_an_enterprise_module():
    """Platform must never be treated as an EnterpriseModule -- it is
    deliberately absent from the policy table, so any permission set,
    however broad, still resolves to inaccessible via this policy."""
    assert is_module_accessible("platform", frozenset({"settings.manage", "audit.read"})) is False


def test_is_module_accessible_false_for_empty_permissions():
    assert is_module_accessible("project_management", frozenset()) is False


def _plant_principal(services, *, permissions: frozenset[str]):
    default_organization = services["platform_runtime_application_service"].get_active_organization()
    real_user = services["auth_service"].register_user(
        f"module-access-planner-{'-'.join(sorted(permissions)) or 'none'}",
        "StrongPass123",
        role_names=["viewer"],
    )
    active_tenant_id = services["tenant_context_service"].get_active_tenant_id()
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id=real_user.id,
            username=real_user.username,
            display_name="Module Access Planner",
            role_names=frozenset(),
            permissions=permissions,
            scoped_access={"organization": {default_organization.id: permissions}},
            active_tenant_id=active_tenant_id,
            active_organization_id=default_organization.id,
        )
    )
    services["user_session"].set_active_organization_id(default_organization.id)


def test_list_accessible_modules_includes_an_enabled_module_the_user_can_use(services):
    app_service = services["platform_runtime_application_service"]
    assert app_service.is_enabled("project_management") is True

    _plant_principal(services, permissions=frozenset({"task.read"}))

    accessible_codes = {module.code for module in app_service.list_accessible_modules()}

    assert "project_management" in accessible_codes


def test_list_accessible_modules_excludes_an_enabled_module_the_user_cannot_use(services):
    """`project_management` is enabled, but a user holding only an
    unrelated permission (no registered project_management prefix) must not
    see it as accessible."""
    app_service = services["platform_runtime_application_service"]
    assert app_service.is_enabled("project_management") is True

    _plant_principal(services, permissions=frozenset({"audit.read"}))

    accessible_codes = {module.code for module in app_service.list_accessible_modules()}

    assert "project_management" not in accessible_codes
