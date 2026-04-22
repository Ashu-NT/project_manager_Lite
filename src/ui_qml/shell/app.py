from __future__ import annotations

import sys

from PySide6.QtGui import QGuiApplication

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml
from src.ui_qml.shell.qml_registry import build_qml_route_registry


def main(argv: list[str] | None = None) -> int:
    app = QGuiApplication(argv or sys.argv)
    registry = build_qml_route_registry()
    engine = create_qml_engine()
    load_qml(engine, registry.get("shell.main").qml_path)
    return app.exec()


__all__ = ["main"]
