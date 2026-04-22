from __future__ import annotations

from pathlib import Path


def create_qml_engine():
    from PySide6.QtQml import QQmlApplicationEngine

    return QQmlApplicationEngine()


def load_qml(engine, qml_path: Path) -> None:
    engine.load(str(qml_path))
    if not engine.rootObjects():
        raise RuntimeError(f"Failed to load QML root: {qml_path}")


__all__ = ["create_qml_engine", "load_qml"]
