from __future__ import annotations

from pathlib import Path
from typing import Any
from PySide6.QtQml import QQmlApplicationEngine

from src.ui_qml.platform.qml_type_registration import register_platform_qml_types
from src.ui_qml.shell.qml_type_registration import register_shell_qml_types

UI_QML_ROOT = Path(__file__).resolve().parents[1]
QML_IMPORT_ROOTS = (
    UI_QML_ROOT / "shared" / "qml",
    UI_QML_ROOT / "shell" / "qml",
    UI_QML_ROOT / "platform" / "qml",
    *(path for path in (UI_QML_ROOT / "modules").glob("*/qml")),
)


def create_qml_engine() -> QQmlApplicationEngine:
    register_shell_qml_types()
    register_platform_qml_types()
    engine = QQmlApplicationEngine()
    for import_root in QML_IMPORT_ROOTS:
        if import_root.exists():
            engine.addImportPath(str(import_root))
    return engine


def expose_context_property(engine: QQmlApplicationEngine, name: str, value: Any) -> None:
    engine.rootContext().setContextProperty(name, value)


def load_qml(
    engine: QQmlApplicationEngine,
    qml_path: Path,
    *,
    initial_properties: dict[str, Any] | None = None,
) -> None:
    if initial_properties is not None:
        engine.setInitialProperties(initial_properties)
    engine.load(str(qml_path))
    if not engine.rootObjects():
        raise RuntimeError(f"Failed to load QML root: {qml_path}")


__all__ = ["create_qml_engine", "expose_context_property", "load_qml"]
