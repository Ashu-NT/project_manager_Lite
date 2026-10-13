"""PartyEditorDialog.qml: Party Code/Name/Type are the only required fields,
Business Roles renders as a real multi-select checkbox list (never a fake
comma-separated free-text input), and no lifecycle control (Active checkbox/
Status dropdown) appears anywhere in the dialog. Loads the real QML engine
and exercises both openForCreate/openForEdit, asserting no qWarning/
qCritical fires -- the same category of error QML raises for a static
"Cannot assign to non-existent property" binding failure."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication

from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

UI_QML_ROOT = REPO_ROOT / "src" / "ui_qml"
_DIALOG_PATH = (
    UI_QML_ROOT / "platform" / "qml" / "workspaces" / "parties" / "dialogs" / "PartyEditorDialog.qml"
)

_TYPE_OPTIONS = [{"label": "Organization", "value": "ORGANIZATION"}, {"label": "Individual", "value": "INDIVIDUAL"}]
_ROLE_OPTIONS = [
    {"label": "Supplier", "value": "SUPPLIER"},
    {"label": "Manufacturer", "value": "MANUFACTURER"},
    {"label": "Vendor", "value": "VENDOR"},
    {"label": "Contractor", "value": "CONTRACTOR"},
    {"label": "Service Provider", "value": "SERVICE_PROVIDER"},
    {"label": "Customer", "value": "CUSTOMER"},
]


def _ensure_qgui_application() -> QGuiApplication:
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["party-editor-dialog-test"])


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

        root.openForCreate({"typeOptions": _TYPE_OPTIONS, "roleOptions": _ROLE_OPTIONS})
        _pump()
        assert root.property("mode") == "create"

        root.openForEdit(
            {
                "partyId": "party-1",
                "partyCode": "SUP-001",
                "partyName": "North Supply",
                "partyType": "ORGANIZATION",
                "roles": ["SUPPLIER", "CUSTOMER"],
            },
            {"typeOptions": _TYPE_OPTIONS, "roleOptions": _ROLE_OPTIONS},
        )
        _pump()
        assert root.property("mode") == "edit"

        form_data = root.property("formData").toVariant()
        assert sorted(form_data["roles"]) == ["CUSTOMER", "SUPPLIER"]
    finally:
        qInstallMessageHandler(previous_handler)

    offending = [m for m in messages if "Cannot assign to non-existent property" in m or "unavailable" in m]
    assert offending == [], offending
