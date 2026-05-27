from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Q_ARG, QObject, QMetaObject
from PySide6.QtGui import QGuiApplication

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml


WORK_REQUESTS_DIALOG_HOST = Path(
    "src/ui_qml/modules/maintenance/qml/workspaces/work_requests/WorkRequestsDialogHost.qml"
)
WORK_ORDERS_DIALOG_HOST = Path(
    "src/ui_qml/modules/maintenance/qml/workspaces/work_orders/WorkOrdersDialogHost.qml"
)
ASSETS_DIALOG_HOST = Path(
    "src/ui_qml/modules/maintenance/qml/workspaces/assets/AssetsDialogHost.qml"
)


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["maintenance-dialog-host-test"])


def _load_host(qml_path: Path, initial_properties: dict) -> tuple[object, QObject]:
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


def test_assets_dialog_host_edit_location_submit_button_emits_update() -> None:
    _, root = _load_host(
        ASSETS_DIALOG_HOST,
        {
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "parentLocationOptions": [{"value": "", "label": "None"}],
            "statusOptions": [{"value": "ACTIVE", "label": "Active"}],
            "criticalityOptions": [{"value": "MEDIUM", "label": "Medium"}],
        },
    )
    captured: list[dict] = []
    root.updateLocationRequested.connect(lambda payload: captured.append(_variant(payload)))
    record = {
        "state": {
            "locationId": "LOC-1",
            "siteId": "SITE-1",
            "locationCode": "LOC-100",
            "name": "Process Area",
            "locationType": "PRODUCTION",
            "status": "ACTIVE",
            "criticality": "MEDIUM",
            "expectedVersion": 3,
        }
    }

    assert QMetaObject.invokeMethod(root, "openEditLocationDialog", Q_ARG("QVariant", record))
    dialog = _find_child(root, "locationEditorDialog")
    _find_child(dialog, "dialogCancelButton")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(dialog, "populateFromRecord")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["locationId"] == "LOC-1"
    assert captured[0]["locationCode"] == "LOC-100"
    assert captured[0]["expectedVersion"] == 3.0


def test_work_request_dialog_host_edit_submit_button_emits_update() -> None:
    _, root = _load_host(
        WORK_REQUESTS_DIALOG_HOST,
        {
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "sourceTypeOptions": [{"value": "MANUAL", "label": "Manual"}],
            "priorityOptions": [{"value": "HIGH", "label": "High"}],
            "statusOptions": [
                {"value": "NEW", "label": "New"},
                {"value": "TRIAGED", "label": "Triaged"},
            ],
        },
    )
    captured: list[dict] = []
    root.updateRequested.connect(lambda payload: captured.append(_variant(payload)))
    record = {
        "state": {
            "workRequestId": "WR-1",
            "siteId": "SITE-1",
            "sourceType": "MANUAL",
            "requestType": "CORRECTIVE",
            "title": "Seal leak on transfer pump",
            "priority": "HIGH",
            "expectedVersion": 2,
        }
    }

    assert QMetaObject.invokeMethod(root, "openEditDialog", Q_ARG("QVariant", record))
    dialog = _find_child(root, "workRequestEditorDialog")
    _find_child(dialog, "dialogCancelButton")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(dialog, "populateFromWorkRequest")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["workRequestId"] == "WR-1"
    assert captured[0]["requestType"] == "CORRECTIVE"
    assert captured[0]["title"] == "Seal leak on transfer pump"
    assert captured[0]["expectedVersion"] == 2.0


def test_work_order_status_dialog_host_submit_button_emits_status_change() -> None:
    _, root = _load_host(
        WORK_ORDERS_DIALOG_HOST,
        {
            "statusOptions": [
                {"value": "DRAFT", "label": "Draft"},
                {"value": "RELEASED", "label": "Released"},
            ]
        },
    )
    captured: list[tuple[str, str, int]] = []
    root.statusChangeRequested.connect(
        lambda work_order_id, status_value, expected_version: captured.append(
            (work_order_id, status_value, int(expected_version))
        )
    )
    record = {
        "title": "Pump overhaul",
        "state": {
            "workOrderId": "WO-1",
            "status": "DRAFT",
            "expectedVersion": 4,
        },
    }

    assert QMetaObject.invokeMethod(root, "openStatusDialog", Q_ARG("QVariant", record))
    dialog = _find_child(root, "workOrderStatusDialog")
    _find_child(dialog, "dialogCancelButton")
    status_combo = _find_child(dialog, "statusCombo")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    status_combo.setProperty("currentIndex", 1)
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert captured == [("WO-1", "RELEASED", 4)]


def test_work_order_dialog_host_cancel_button_does_not_emit_create() -> None:
    _, root = _load_host(
        WORK_ORDERS_DIALOG_HOST,
        {
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "sourceTypeOptions": [{"value": "MANUAL", "label": "Manual"}],
            "workOrderTypeOptions": [{"value": "CORRECTIVE", "label": "Corrective"}],
            "priorityOptions": [{"value": "HIGH", "label": "High"}],
            "vendorOptions": [{"value": "", "label": "None"}],
        },
    )
    created: list[dict] = []
    root.createRequested.connect(lambda payload: created.append(_variant(payload)))

    assert QMetaObject.invokeMethod(root, "openCreateDialog")
    dialog = _find_child(root, "workOrderEditorDialog")
    cancel_button = _find_child(dialog, "dialogCancelButton")
    assert QMetaObject.invokeMethod(cancel_button, "click")

    assert created == []

