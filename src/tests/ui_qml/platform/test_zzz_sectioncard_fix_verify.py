from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtQuick import QQuickItem

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.context import build_shell_context
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml
from src.ui_qml.shell.qml_registry import build_qml_route_registry

OUT_DIR = Path(
    r"C:\Users\ashu\AppData\Local\Temp\claude\C--Users-ashu-Desktop-PersonalProjects-project-manager-Lite\ff316d5a-9964-4be6-9afa-dc0afa4b8ad1\scratchpad\visual_qa"
)


def _settle(app, seconds=2.0):
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)


def _find(obj, object_name):
    if obj.objectName() == object_name:
        return obj
    children = obj.childItems() if isinstance(obj, QQuickItem) else obj.children()
    for child in children:
        found = _find(child, object_name)
        if found is not None:
            return found
    return None


def _grab(qapp, item, path):
    grab_result = item.grabToImage()
    state = {}
    def _on_ready():
        state["done"] = grab_result.saveToFile(str(path))
    grab_result.ready.connect(_on_ready)
    deadline = time.time() + 5
    while "done" not in state and time.time() < deadline:
        qapp.processEvents()
    return state.get("done")


def test_sectioncard_fix_verify(qapp, services):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    registry = build_qml_route_registry()
    shell_context = build_shell_context(build_main_window_navigation(registry))
    api_registry = build_desktop_api_registry(services)
    platform_catalog = PlatformWorkspaceCatalog(desktop_api_registry=api_registry)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=api_registry)

    engine = create_qml_engine()
    shell_route = registry.get("shell.app")
    load_qml(
        engine,
        shell_route.qml_path,
        initial_properties={
            "shellModel": shell_context,
            "platformCatalog": platform_catalog,
            "pmCatalog": pm_catalog,
        },
    )
    root = engine.rootObjects()[0]
    root.resize(1600, 1000)
    shell_context.selectRoute("platform.workspace")
    _settle(qapp)
    platform_catalog.selectDestination("organizations")
    _settle(qapp)
    main_window = root.findChild(QQuickItem, "mainWindow")
    org_loader = _find(main_window, "organizationsLoader")
    org_page = org_loader.property("item")
    items = platform_catalog.adminWorkspace.organizations.get("items", [])
    org_id = items[0]["id"]
    org_page.setProperty("selectedRowId", org_id)
    org_page.setProperty("detailOpen", True)
    _settle(qapp)
    print("saved:", _grab(qapp, main_window, OUT_DIR / "sectioncard_fix_wide.png"))

    root.resize(1000, 1700)
    _settle(qapp)
    print("saved narrow:", _grab(qapp, main_window, OUT_DIR / "sectioncard_fix_narrow.png"))
