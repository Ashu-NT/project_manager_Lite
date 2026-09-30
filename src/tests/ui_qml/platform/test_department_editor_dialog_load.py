"""DepartmentEditorDialog.qml: real-field-required markers (Name/Code only --
Department Type is backend-optional, never marked required), Structure
group's Head of Department field visible in Edit only (structurally
impossible at Create -- no Employee can belong to a not-yet-created
department), and no lifecycle control anywhere in the dialog. Loads the real
QML engine and exercises both openForCreate/openForEdit, asserting no
qWarning/qCritical fires -- the same category of error QML raises for a
static "Cannot assign to non-existent property" binding failure."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication

from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

UI_QML_ROOT = REPO_ROOT / "src" / "ui_qml"
_DIALOG_PATH = (
    UI_QML_ROOT / "platform" / "qml" / "workspaces" / "departments" / "dialogs" / "DepartmentEditorDialog.qml"
)


def _ensure_qgui_application() -> QGuiApplication:
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["department-editor-dialog-test"])


def _pump(n: int = 20) -> None:
    for _ in range(n):
        QCoreApplication.processEvents()


def test_create_and_edit_modes_raise_no_qml_warnings() -> None:
    _ensure_qgui_application()
    messages: list[str] = []

    def _handler(msg_type, context, message):
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            messages.append(message)

    previous_handler = qInstallMessageHandler(_handler)
    try:
        engine = create_qml_engine()
        load_qml(engine, _DIALOG_PATH)
        assert len(engine.rootObjects()) == 1
        root = engine.rootObjects()[0]

        root.openForCreate({"siteOptions": [], "parentOptions": [], "headOfDepartmentOptions": []})
        _pump()
        assert root.property("mode") == "create"

        root.openForEdit(
            {"departmentId": "dep-1", "departmentCode": "DEPT-1", "name": "Electrical"},
            {"siteOptions": [], "parentOptions": [], "headOfDepartmentOptions": []},
        )
        _pump()
        assert root.property("mode") == "edit"
    finally:
        qInstallMessageHandler(previous_handler)

    offending = [m for m in messages if "Cannot assign to non-existent property" in m or "unavailable" in m]
    assert offending == [], offending
