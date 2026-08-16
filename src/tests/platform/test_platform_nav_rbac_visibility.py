"""Frontend RBAC visibility -- the QML nav previously showed the same static
14-item list to every user regardless of their actual backend permissions,
and every workspace controller was eagerly constructed+refreshed at
startup regardless of what the user could access. This adds a real
permission-derived visibility check the shell nav (and, going forward,
individual workspace pages) can use: PlatformRuntimeApplicationService.
get_current_permissions() reads the current session principal's already-
resolved permission set (no extra query -- it's computed once at login),
exposed through PlatformRuntimeDesktopApi and then PlatformWorkspaceCatalog.
hasPermission()/hasAnyPermission(), which PlatformNavigation.qml uses to
filter its destination list.

This does not yet address the eager-construction/refresh problem identified
alongside it (a separate, larger change) -- it only closes the "user sees a
nav item they have no permission for" gap.
"""
from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def test_platform_admin_sees_all_permissions(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    # The default `services` principal is the bootstrap "admin" user, which
    # carries "platform.admin" (and effectively everything else).
    assert catalog.hasPermission("platform.admin")
    assert catalog.hasPermission("settings.manage")
    assert catalog.hasAnyPermission(["employee.read"])
    assert catalog.hasAnyPermission(["nonexistent.permission", "platform.admin"])


def test_no_principal_denies_everything():
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=None)

    assert not catalog.hasPermission("settings.manage")
    assert not catalog.hasAnyPermission(["settings.manage", "platform.admin"])


def test_restricted_principal_only_sees_its_own_permissions(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    user_session = services["user_session"]
    original_principal = user_session.principal
    restricted_principal = UserSessionPrincipal(
        user_id=original_principal.user_id,
        username=original_principal.username,
        display_name=original_principal.display_name,
        role_names=frozenset({"employee_viewer"}),
        permissions=frozenset({"employee.read"}),
    )
    user_session.set_principal(restricted_principal)
    try:
        catalog.refreshCurrentPermissions()

        assert catalog.hasPermission("employee.read")
        assert not catalog.hasPermission("settings.manage")
        assert not catalog.hasPermission("platform.admin")
        assert not catalog.hasAnyPermission(["settings.manage", "site.read"])
        assert catalog.hasAnyPermission(["settings.manage", "employee.read"])
    finally:
        user_session.set_principal(original_principal)
        catalog.refreshCurrentPermissions()


def test_refresh_current_permissions_picks_up_principal_change(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    assert catalog.hasPermission("platform.admin")

    user_session = services["user_session"]
    original_principal = user_session.principal
    user_session.set_principal(
        UserSessionPrincipal(
            user_id=original_principal.user_id,
            username=original_principal.username,
            display_name=original_principal.display_name,
            role_names=frozenset(),
            permissions=frozenset(),
        )
    )
    try:
        # Without a refresh, the catalog still reflects what it cached at
        # construction time.
        assert catalog.hasPermission("platform.admin")

        catalog.refreshCurrentPermissions()
        assert not catalog.hasPermission("platform.admin")
    finally:
        user_session.set_principal(original_principal)
        catalog.refreshCurrentPermissions()
