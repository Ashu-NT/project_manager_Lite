"""Lazy-loading lifecycle for the four secondary Platform workspace
controllers (Access, Support, Control, Settings): construction must not
fetch data, ensureLoaded() triggers exactly one first-use load, a repeat
ensureLoaded() is a no-op, refresh() always re-fetches, and permission-
aware suppression fails open when permission data is unavailable."""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.platform.presenters.identity_access.access.access_workspace_presenter import (
    PlatformAccessWorkspacePresenter,
)
from src.ui_qml.platform.presenters.support.support_workspace_presenter import (
    PlatformSupportWorkspacePresenter,
)
from src.ui_qml.platform.presenters.control.control_queue_presenter import (
    PlatformControlQueuePresenter,
)
from src.ui_qml.platform.presenters.settings.settings_catalog_presenter import (
    PlatformSettingsCatalogPresenter,
)


def _instrument(cls, method_name):
    counts = {method_name: 0}
    real = getattr(cls, method_name)

    def counting(self, *args, **kwargs):
        counts[method_name] += 1
        return real(self, *args, **kwargs)

    setattr(cls, method_name, counting)

    def restore():
        setattr(cls, method_name, real)

    return counts, restore


def _restricted_principal(original_principal):
    return UserSessionPrincipal(
        user_id=original_principal.user_id,
        username=original_principal.username,
        display_name=original_principal.display_name,
        role_names=frozenset(),
        permissions=frozenset(),
    )


# Each entry: (controller attribute on the catalog, presenter class whose
# unconditionally-called refresh() method we count fetches by, that
# method's name, a domain event signal the controller listens to, and the
# permission code(s) that gate it -- None for Support, which has no gate).
_CASES = [
    (
        "adminAccessWorkspace",
        PlatformAccessWorkspacePresenter,
        "build_security_users",
        domain_events.access_changed,
        ("access.manage",),
    ),
    (
        "adminSupportWorkspace",
        PlatformSupportWorkspacePresenter,
        "build_settings_state",
        None,
        None,
    ),
    (
        "controlWorkspace",
        PlatformControlQueuePresenter,
        "build_approval_queue",
        domain_events.approvals_changed,
        ("approval.request", "approval.decide", "audit.read"),
    ),
    (
        "settingsWorkspace",
        PlatformSettingsCatalogPresenter,
        "build_module_entitlements",
        domain_events.modules_changed,
        ("settings.manage",),
    ),
]


def test_construction_does_not_eagerly_refresh_any_secondary_workspace(services):
    """Building the catalog must be side-effect free for all four
    controllers -- none of their data-fetching presenter methods fire
    until something actually activates that workspace."""
    instruments = [(_instrument(cls, name)) for _, cls, name, _, _ in _CASES]
    try:
        registry = build_desktop_api_registry(services)
        catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    finally:
        for counts, restore in instruments:
            restore()

    for (attr, _, name, _, _), (counts, _) in zip(_CASES, instruments):
        assert counts[name] == 0, f"{attr} fetched data during construction"
        controller = getattr(catalog, attr)
        assert controller._loaded is False


def test_ensure_loaded_lifecycle_per_secondary_workspace(services):
    """For each controller: first ensureLoaded() fetches once, a second
    ensureLoaded() does not re-fetch, and an explicit refresh() always
    re-fetches regardless of loaded state."""
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    for attr, cls, name, _, _ in _CASES:
        controller = getattr(catalog, attr)
        counts, restore = _instrument(cls, name)
        try:
            assert controller._loaded is False

            controller.ensureLoaded()
            assert counts[name] == 1, f"{attr} did not load on first ensureLoaded()"
            assert controller._loaded is True

            controller.ensureLoaded()
            assert counts[name] == 1, f"{attr} refetched on a redundant ensureLoaded()"

            controller.refresh()
            assert counts[name] == 2, f"{attr} explicit refresh() did not re-fetch"
        finally:
            restore()


def test_domain_event_does_not_force_load_of_unvisited_workspace(services):
    """Invalidating an entity a lazy controller cares about, before that
    controller has ever been activated, must not force a background
    fetch -- only the eventual first ensureLoaded() should load it."""
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    for attr, cls, name, signal, _ in _CASES:
        if signal is None:
            continue
        controller = getattr(catalog, attr)
        counts, restore = _instrument(cls, name)
        try:
            signal.emit("some-entity-id")
            assert counts[name] == 0, f"{attr} was force-loaded by a domain event while unvisited"
            assert controller._loaded is False

            controller.ensureLoaded()
            assert counts[name] == 1

            signal.emit("some-entity-id")
            assert counts[name] == 2, f"{attr} did not react to invalidation once loaded"
        finally:
            restore()


def test_permission_aware_suppression_for_gated_secondary_workspaces(services):
    """A session with none of a gated controller's required permissions
    must not trigger that controller's initial load via ensureLoaded();
    explicit refresh() is unaffected since backend authorization -- not
    this client-side pre-filter -- remains the real boundary."""
    user_session = services["user_session"]
    original_principal = user_session.principal
    restricted = _restricted_principal(original_principal)

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    user_session.set_principal(restricted)
    catalog.refreshCurrentPermissions()

    try:
        for attr, cls, name, _, permission_codes in _CASES:
            if permission_codes is None:
                continue
            controller = getattr(catalog, attr)
            counts, restore = _instrument(cls, name)
            try:
                controller.ensureLoaded()
                assert counts[name] == 0, f"{attr} loaded despite no granted permission"
                assert controller._loaded is False

                # Explicit refresh always works -- suppression is a
                # loading optimization only, never an authorization gate.
                controller.refresh()
                assert counts[name] == 1
            finally:
                restore()
    finally:
        user_session.set_principal(original_principal)
        catalog.refreshCurrentPermissions()


def test_support_workspace_has_no_permission_gate(services):
    """Support/Diagnostics is not gated by any permission code -- it
    lazy-loads on first use regardless of the session's permissions."""
    user_session = services["user_session"]
    original_principal = user_session.principal
    restricted = _restricted_principal(original_principal)

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    user_session.set_principal(restricted)
    catalog.refreshCurrentPermissions()

    counts, restore = _instrument(PlatformSupportWorkspacePresenter, "build_settings_state")
    try:
        catalog.adminSupportWorkspace.ensureLoaded()
        assert counts["build_settings_state"] == 1
    finally:
        restore()
        user_session.set_principal(original_principal)
        catalog.refreshCurrentPermissions()


def test_secondary_workspace_controllers_fail_open_without_runtime_api():
    """A controller constructed directly with no runtime_api wired (e.g.
    in isolation, outside the catalog) must keep loading on first use --
    permission suppression never applies when permission data itself
    can't be determined."""
    from src.ui_qml.platform.controllers.identity_access.access.access_workspace_controller import (
        PlatformAdminAccessWorkspaceController,
    )
    from src.ui_qml.platform.controllers.control.control_workspace_controller import (
        PlatformControlWorkspaceController,
    )
    from src.ui_qml.platform.controllers.settings.settings_workspace_controller import (
        PlatformSettingsWorkspaceController,
    )
    from src.ui_qml.platform.presenters.identity_access.access.access_workspace_presenter import (
        PlatformAccessWorkspacePresenter,
    )
    from src.ui_qml.platform.presenters.control.control_presenter import (
        PlatformControlWorkspacePresenter,
    )
    from src.ui_qml.platform.presenters.settings.settings_presenter import (
        PlatformSettingsWorkspacePresenter,
    )

    access = PlatformAdminAccessWorkspaceController(
        presenter=PlatformAccessWorkspacePresenter(access_api=None, user_api=None),
        # runtime_api intentionally omitted
    )
    control = PlatformControlWorkspaceController(
        overview_presenter=PlatformControlWorkspacePresenter(approval_api=None, audit_api=None),
        queue_presenter=PlatformControlQueuePresenter(approval_api=None, audit_api=None),
        # runtime_api intentionally omitted
    )
    settings = PlatformSettingsWorkspaceController(
        overview_presenter=PlatformSettingsWorkspacePresenter(runtime_api=None),
        catalog_presenter=PlatformSettingsCatalogPresenter(runtime_api=None, integration_api=None),
        # runtime_api intentionally omitted
    )

    for controller in (access, control, settings):
        assert controller._loaded is False
        controller.ensureLoaded()
        assert controller._loaded is True
