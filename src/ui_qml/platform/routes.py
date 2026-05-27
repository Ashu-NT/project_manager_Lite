from __future__ import annotations

from pathlib import Path

from src.ui_qml.shell.routes import QmlRoute


def platform_qml_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent / "qml" / Path(*parts)


def build_platform_routes() -> list[QmlRoute]:
    return [
        QmlRoute(
            route_id="platform.admin",
            module_code="platform",
            module_label="Platform",
            group_label="Administration",
            title="Admin Console",
            qml_path=platform_qml_path("workspaces", "admin", "AdminWorkspace.qml"),
            presenter_key="platform.admin",
        ),
        QmlRoute(
            route_id="platform.control",
            module_code="platform",
            module_label="Platform",
            group_label="Control",
            title="Control Center",
            qml_path=platform_qml_path("workspaces", "control", "ControlWorkspace.qml"),
            presenter_key="platform.control",
        ),
        QmlRoute(
            route_id="platform.settings",
            module_code="platform",
            module_label="Platform",
            group_label="Settings",
            title="Settings",
            qml_path=platform_qml_path("workspaces", "settings", "SettingsWorkspace.qml"),
            presenter_key="platform.settings",
        ),
    ]


__all__ = ["build_platform_routes", "platform_qml_path"]
