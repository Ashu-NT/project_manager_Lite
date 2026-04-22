from __future__ import annotations

import sys

from PySide6.QtGui import QGuiApplication

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.shell.context import build_shell_context
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_engine import (
    create_qml_engine,
    expose_context_property,
    load_qml,
)
from src.ui_qml.shell.qml_registry import build_qml_route_registry


def main(argv: list[str] | None = None) -> int:
    app = QGuiApplication(argv or sys.argv)
    registry = build_qml_route_registry()
    shell_context = build_shell_context(build_main_window_navigation(registry))
    pm_workspace_catalog = ProjectManagementWorkspaceCatalog()
    engine = create_qml_engine()
    expose_context_property(engine, "shellContext", shell_context)
    expose_context_property(engine, "pmWorkspaceCatalog", pm_workspace_catalog)
    load_qml(engine, registry.get("shell.app").qml_path)
    return app.exec()


__all__ = ["main"]
