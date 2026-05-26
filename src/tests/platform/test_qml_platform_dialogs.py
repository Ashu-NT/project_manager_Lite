from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Q_ARG, QObject, QMetaObject
from PySide6.QtGui import QGuiApplication

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml


APPROVAL_DECISION_DIALOG = Path(
    "src/ui_qml/platform/qml/Platform/Dialogs/ApprovalDecisionDialog.qml"
)
ORGANIZATION_EDITOR_DIALOG = Path(
    "src/ui_qml/platform/qml/Platform/Dialogs/OrganizationEditorDialog.qml"
)


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["platform-dialog-test"])


def _load_dialog(qml_path: Path, initial_properties: dict) -> tuple[object, QObject]:
    _ensure_qgui_application()
    engine = create_qml_engine()
    load_qml(engine, qml_path.resolve(), initial_properties=initial_properties)
    root = engine.rootObjects()[0]
    return engine, root


def _find_child(root: QObject, name: str) -> QObject:
    child = root.findChild(QObject, name)
    assert child is not None, f"Expected child object {name!r}"
    return child


def _variant(value):
    return value.toVariant() if hasattr(value, "toVariant") else value


def test_approval_decision_dialog_submit_button_emits_decision() -> None:
    _, root = _load_dialog(APPROVAL_DECISION_DIALOG, {})
    captured: list[tuple[str, str, str]] = []
    root.decisionConfirmed.connect(
        lambda mode, request_id, note: captured.append(
            (str(mode), str(request_id), str(note))
        )
    )

    assert QMetaObject.invokeMethod(
        root,
        "openForDecision",
        Q_ARG("QVariant", "approve"),
        Q_ARG("QVariant", {"id": "APR-1", "title": "Approve access role"}),
    )
    _find_child(root, "dialogCancelButton")
    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert captured == [("approve", "APR-1", "")]


def test_organization_editor_dialog_submit_button_emits_save_requested() -> None:
    _, root = _load_dialog(
        ORGANIZATION_EDITOR_DIALOG,
        {"moduleOptions": [{"value": "pm", "label": "Project Management"}]},
    )
    captured: list[tuple[str, dict]] = []
    root.saveRequested.connect(
        lambda mode, payload: captured.append((str(mode), _variant(payload)))
    )

    draft = {
        "organizationId": "ORG-1",
        "version": 3,
        "organizationCode": "ACME",
        "displayName": "Acme Manufacturing",
        "timezoneName": "UTC",
        "baseCurrency": "EUR",
        "isActive": True,
        "initialModuleCodes": ["pm"],
    }
    assert QMetaObject.invokeMethod(root, "openForEdit", Q_ARG("QVariant", draft))
    _find_child(root, "dialogCancelButton")
    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0][0] == "edit"
    assert captured[0][1]["organizationId"] == "ORG-1"
    assert captured[0][1]["organizationCode"] == "ACME"
    assert captured[0][1]["baseCurrency"] == "EUR"

