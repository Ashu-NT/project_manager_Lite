from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class QmlRoute:
    """A shell route to a QML component and its presenter factory key."""

    route_id: str
    module_code: str
    module_label: str
    group_label: str
    title: str
    qml_path: Path
    presenter_key: str | None = None


def shell_qml_path(file_name: str) -> Path:
    return Path(__file__).resolve().parent / "qml" / file_name


def build_shell_routes() -> list[QmlRoute]:
    return [
        QmlRoute(
            route_id="shell.main",
            module_code="shell",
            module_label="Shell",
            group_label="Runtime",
            title="Main Window",
            qml_path=shell_qml_path("MainWindow.qml"),
        )
    ]


__all__ = ["QmlRoute", "build_shell_routes", "shell_qml_path"]
