from __future__ import annotations

from pathlib import Path

from src.ui_qml.shell.routes import QmlRoute


def platform_qml_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent / "qml" / Path(*parts)


def build_platform_routes() -> list[QmlRoute]:
    return [
        QmlRoute(
            route_id="platform.workspace",
            module_code="platform",
            module_label="Platform",
            group_label="Platform",
            title="Platform",
            qml_path=platform_qml_path("workspace", "PlatformWorkspace.qml"),
            presenter_key=None,
        ),
    ]


__all__ = ["build_platform_routes", "platform_qml_path"]
