"""Context-level (Level 2) invalidation safety: when a scope/permission
change makes the currently-selected Platform destination inaccessible, the
catalog must redirect to a safe destination (Overview, since it is always
accessible) rather than leave an inaccessible workspace visible."""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def _restricted_principal(original_principal, *, permissions: frozenset[str]):
    return UserSessionPrincipal(
        user_id=original_principal.user_id,
        username=original_principal.username,
        display_name=original_principal.display_name,
        role_names=frozenset(),
        permissions=permissions,
    )


def test_current_destination_redirects_to_overview_when_permission_is_lost(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    catalog.selectDestination("control_audit")
    assert catalog.currentDestinationId == "control_audit"

    user_session = services["user_session"]
    original_principal = user_session.principal
    try:
        user_session.set_principal(_restricted_principal(original_principal, permissions=frozenset({"employee.read"})))
        catalog.refreshCurrentPermissions()

        assert catalog.currentDestinationId == "overview"
    finally:
        user_session.set_principal(original_principal)
        catalog.refreshCurrentPermissions()


def test_current_destination_is_left_unchanged_when_still_accessible(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    catalog.selectDestination("employees")

    user_session = services["user_session"]
    original_principal = user_session.principal
    try:
        # "employee.read" is kept, so "employees" must remain the current
        # destination even though most other permissions are dropped.
        user_session.set_principal(
            _restricted_principal(original_principal, permissions=frozenset({"employee.read"}))
        )
        catalog.refreshCurrentPermissions()

        assert catalog.currentDestinationId == "employees"
    finally:
        user_session.set_principal(original_principal)
        catalog.refreshCurrentPermissions()


def test_redirect_prefers_overview_over_any_other_still_accessible_destination(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    catalog.selectDestination("control_audit")

    user_session = services["user_session"]
    original_principal = user_session.principal
    try:
        # Grants "employees" access too -- Overview must still be chosen
        # over it, since Overview is the documented preferred safe target.
        user_session.set_principal(
            _restricted_principal(original_principal, permissions=frozenset({"employee.read"}))
        )
        catalog.refreshCurrentPermissions()

        assert catalog.currentDestinationId == "overview"
    finally:
        user_session.set_principal(original_principal)
        catalog.refreshCurrentPermissions()


def test_regaining_permission_does_not_move_user_away_from_overview(services):
    """Redirecting to Overview is a one-time safety action, not a sticky
    state -- once on Overview, a later permission refresh (even one that
    grants everything back) must not auto-navigate the user anywhere; they
    stay on Overview until they choose to navigate."""
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    catalog.selectDestination("control_audit")

    user_session = services["user_session"]
    original_principal = user_session.principal
    try:
        user_session.set_principal(_restricted_principal(original_principal, permissions=frozenset()))
        catalog.refreshCurrentPermissions()
        assert catalog.currentDestinationId == "overview"

        user_session.set_principal(original_principal)
        catalog.refreshCurrentPermissions()
        assert catalog.currentDestinationId == "overview"
    finally:
        user_session.set_principal(original_principal)
        catalog.refreshCurrentPermissions()
