from __future__ import annotations

import sys

from PySide6.QtGui import QGuiApplication

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.context import build_shell_context
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_engine import (
    create_qml_engine,
    load_qml,
)
from src.ui_qml.shell.qml_registry import build_qml_route_registry


def main(argv: list[str] | None = None, desktop_api_registry: object | None = None) -> int:
    app = QGuiApplication(argv or sys.argv)
    registry = build_qml_route_registry()
    shell_context = build_shell_context(build_main_window_navigation(registry))
    platform_workspace_catalog = PlatformWorkspaceCatalog(
        getattr(desktop_api_registry, "platform_runtime", None) if desktop_api_registry is not None else None,
        desktop_api_registry=desktop_api_registry,
    )
    pm_workspace_catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=desktop_api_registry,
    )
    engine = create_qml_engine()
    load_qml(
        engine,
        registry.get("shell.app").qml_path,
        initial_properties={
            "shellModel": shell_context,
            "platformCatalog": platform_workspace_catalog,
            "pmCatalog": pm_workspace_catalog,
        },
    )
    return app.exec()


__all__ = ["main"]
