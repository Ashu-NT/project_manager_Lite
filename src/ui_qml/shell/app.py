from __future__ import annotations

import sys

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


def main(argv: list[str] | None = None, desktop_api_registry: object | None = None) -> int:
    app = QGuiApplication(argv or sys.argv)
    registry = build_qml_route_registry()
    shell_context = build_shell_context(build_main_window_navigation(registry))
    platform_runtime_api = (
        getattr(desktop_api_registry, "platform_runtime", None)
        if desktop_api_registry is not None
        else None
    )
    platform_workspace_catalog = PlatformWorkspaceCatalog(platform_runtime_api)
    pm_workspace_catalog = ProjectManagementWorkspaceCatalog()
    engine = create_qml_engine()
    expose_context_property(engine, "shellContext", shell_context)
    expose_context_property(engine, "platformWorkspaceCatalog", platform_workspace_catalog)
    expose_context_property(engine, "pmWorkspaceCatalog", pm_workspace_catalog)
    load_qml(engine, registry.get("shell.app").qml_path)
    return app.exec()


__all__ = ["main"]
