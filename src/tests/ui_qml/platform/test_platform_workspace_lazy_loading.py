"""Platform's workspace host must instantiate each destination surface's
QML item only on first activation, and reuse the same instance thereafter."""

from __future__ import annotations

import os

from PySide6.QtGui import QGuiApplication

from src.application.runtime import build_desktop_api_registry
from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

PAGE_PATH = REPO_ROOT / "src/ui_qml/platform/qml/workspace/PlatformWorkspacePage.qml"


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["platform-lazy-loading-test"])


def _find_by_object_name(obj, name):
    if obj.objectName() == name:
        return obj
    for child in obj.children():
        found = _find_by_object_name(child, name)
        if found is not None:
            return found
    return None


def _load_page(services):
    _ensure_qgui_application()
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    engine = create_qml_engine()
    load_qml(engine, PAGE_PATH, initial_properties={"platformCatalog": catalog})
    root = engine.rootObjects()[0]
    return engine, root, catalog


_ALL_LOADER_NAMES = (
    "overviewLoader",
    "usersLoader",
    "accessLoader",
    "documentsLoader",
    "structuresLoader",
    "organizationsLoader",
    "sitesLoader",
    "departmentsLoader",
    "employeesLoader",
    "partiesLoader",
    "calendarsLoader",
    "controlLoader",
    "settingsLoader",
    "tenantsLoader",
)


def test_only_overview_is_instantiated_on_first_entry(services) -> None:
    _engine, root, _catalog = _load_page(services)

    overview_loader = _find_by_object_name(root, "overviewLoader")
    assert overview_loader.property("item") is not None

    for name in _ALL_LOADER_NAMES:
        if name == "overviewLoader":
            continue
        loader = _find_by_object_name(root, name)
        assert loader.property("active") is False, name
        assert loader.property("item") is None, name


def test_visiting_a_destination_instantiates_only_that_loader(services) -> None:
    _engine, root, catalog = _load_page(services)

    catalog.selectDestination("sites")

    sites_loader = _find_by_object_name(root, "sitesLoader")
    assert sites_loader.property("active") is True
    assert sites_loader.property("item") is not None

    for name in _ALL_LOADER_NAMES:
        if name in ("overviewLoader", "sitesLoader"):
            continue
        loader = _find_by_object_name(root, name)
        assert loader.property("active") is False, name


def test_revisiting_a_destination_reuses_the_same_instance(services) -> None:
    _engine, root, catalog = _load_page(services)

    catalog.selectDestination("sites")
    sites_loader = _find_by_object_name(root, "sitesLoader")
    first_item = sites_loader.property("item")
    assert first_item is not None

    catalog.selectDestination("overview")
    catalog.selectDestination("sites")

    second_item = sites_loader.property("item")
    assert second_item is not None
    assert first_item == second_item


def test_previously_visited_destination_stays_loaded_after_leaving_it(services) -> None:
    _engine, root, catalog = _load_page(services)

    catalog.selectDestination("sites")
    catalog.selectDestination("employees")

    sites_loader = _find_by_object_name(root, "sitesLoader")
    employees_loader = _find_by_object_name(root, "employeesLoader")

    assert sites_loader.property("active") is True
    assert sites_loader.property("item") is not None
    assert sites_loader.property("visible") is False

    assert employees_loader.property("active") is True
    assert employees_loader.property("visible") is True


def test_control_surface_shared_by_two_destinations_loads_once(services) -> None:
    _engine, root, catalog = _load_page(services)

    catalog.selectDestination("control_approvals")
    control_loader = _find_by_object_name(root, "controlLoader")
    first_item = control_loader.property("item")
    assert first_item is not None

    catalog.selectDestination("control_audit")
    second_item = control_loader.property("item")
    assert second_item is not None
    assert first_item == second_item


def test_related_record_navigation_loads_target_surface_synchronously(services) -> None:
    """openRecord() is called on the target Loader's freshly-created item in
    the same call that switches activeDestination -- the target surface
    must already be instantiated by the time that call runs."""
    from PySide6.QtCore import QMetaObject, Q_ARG

    _engine, root, _catalog = _load_page(services)

    ok = QMetaObject.invokeMethod(
        root,
        "_onRelatedRecordRequested",
        Q_ARG("QVariant", "sites"),
        Q_ARG("QVariant", "site-123"),
    )
    assert ok is True

    assert root.property("activeDestination") == "sites"
    sites_loader = _find_by_object_name(root, "sitesLoader")
    assert sites_loader.property("active") is True
    assert sites_loader.property("item") is not None
    assert str(sites_loader.property("item").property("selectedRowId")) == "site-123"
