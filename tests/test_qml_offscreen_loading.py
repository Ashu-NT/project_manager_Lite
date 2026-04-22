from __future__ import annotations

import os

from PySide6.QtGui import QGuiApplication

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.context import build_shell_context
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_engine import (
    create_qml_engine,
    expose_context_property,
    load_qml,
)
from src.ui_qml.shell.qml_registry import build_qml_route_registry


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["qml-offscreen-test"])


def test_registered_qml_routes_load_offscreen() -> None:
    _ensure_qgui_application()
    registry = build_qml_route_registry()
    engine = create_qml_engine()
    shell_context = build_shell_context(build_main_window_navigation(registry))

    expose_context_property(engine, "shellContext", shell_context)
    expose_context_property(engine, "platformWorkspaceCatalog", PlatformWorkspaceCatalog())
    expose_context_property(engine, "pmWorkspaceCatalog", ProjectManagementWorkspaceCatalog())

    for route in registry.list_routes():
        load_qml(engine, route.qml_path)

    assert len(engine.rootObjects()) == len(registry.list_routes())
