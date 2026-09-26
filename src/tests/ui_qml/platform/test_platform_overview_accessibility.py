"""Platform Overview: KPI tiles must only be clickable when their target
destination is actually present in the (already permission-filtered)
Context Navigation Tree -- never a blanket "all KPIs are clickable" switch
that could expose a destination the current session cannot reach."""

from __future__ import annotations

from PySide6.QtQuick import QQuickItem

from src.application.runtime import build_desktop_api_registry
from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

PAGE_PATH = REPO_ROOT / "src/ui_qml/platform/qml/workspace/PlatformWorkspacePage.qml"


def _find_by_object_name(obj, name):
    if obj.objectName() == name:
        return obj
    children = obj.childItems() if isinstance(obj, QQuickItem) else obj.children()
    for child in children:
        found = _find_by_object_name(child, name)
        if found is not None:
            return found
    return None


def _load_page(services, catalog):
    engine = create_qml_engine()
    load_qml(engine, PAGE_PATH, initial_properties={"platformCatalog": catalog})
    root = engine.rootObjects()[0]
    return engine, root


def test_kpi_tiles_are_only_clickable_when_destination_is_accessible(services) -> None:
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
        _engine, root = _load_page(services, catalog)

        organizations_tile = _find_by_object_name(root, "overviewMetricTile_Organizations")
        users_tile = _find_by_object_name(root, "overviewMetricTile_Users")
        approvals_tile = _find_by_object_name(root, "overviewMetricTile_Pending approvals")
        documents_tile = _find_by_object_name(root, "overviewMetricTile_Documents")

        # employee_viewer holds only employee.read -- none of these four
        # destinations (settings.manage / auth.* / approval.*) are
        # accessible, so none of their KPI tiles may present as clickable.
        for tile in (organizations_tile, users_tile, approvals_tile, documents_tile):
            assert tile is not None
            assert tile.property("clickable") is False
    finally:
        user_session.set_principal(original_principal)


def test_kpi_tiles_are_clickable_when_destination_is_accessible(services) -> None:
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    # Default `services` principal is the bootstrap admin -- holds every
    # permission, so every destination-backed KPI tile should be clickable.
    _engine, root = _load_page(services, catalog)

    organizations_tile = _find_by_object_name(root, "overviewMetricTile_Organizations")
    assert organizations_tile is not None
    assert organizations_tile.property("clickable") is True
