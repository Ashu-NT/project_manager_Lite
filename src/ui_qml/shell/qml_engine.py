from __future__ import annotations

from pathlib import Path
from typing import Any
from PySide6.QtQml import QQmlApplicationEngine

def create_qml_engine() -> QQmlApplicationEngine:
    return QQmlApplicationEngine()


def expose_context_property(engine:QQmlApplicationEngine, name: str, value: Any) -> None:
    engine.rootContext().setContextProperty(name, value)


def load_qml(engine:QQmlApplicationEngine, qml_path: Path) -> None:
    engine.load(str(qml_path))
    if not engine.rootObjects():
        raise RuntimeError(f"Failed to load QML root: {qml_path}")


__all__ = ["create_qml_engine", "expose_context_property", "load_qml"]
