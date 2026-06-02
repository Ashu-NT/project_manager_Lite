from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Q_ARG, Property, QObject, QMetaObject, Signal, Slot
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


class _MockController(QObject):
    """Records the controller calls the dialog hosts make and returns success.

    The refactored hosts no longer emit ``*Requested`` signals; instead each
    ``onSubmitted`` handler calls ``root.workspaceController.<method>(payload)``
    directly and passes the result to ``_handleResult`` (which closes the dialog
    when ``result.ok !== false``). This mock therefore returns ``{"ok": True}``
    for every method so the dialog closes, while recording the call for assertion.
    """

    _changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, object]] = []

    def _rec(self, name, payload):
        self.calls.append((name, payload))
        return {"ok": True}

    def last(self, name: str):
        for call_name, payload in reversed(self.calls):
            if call_name == name:
                return payload
        raise AssertionError(f"No recorded call for {name!r}; calls={self.calls!r}")

    def count(self, name: str) -> int:
        return sum(1 for call_name, _ in self.calls if call_name == name)

    @Property(bool, notify=_changed)
    def isBusy(self):
        return False

    @Property(bool, notify=_changed)
    def isLoading(self):
        return False

    @Property(str, notify=_changed)
    def errorMessage(self):
        return ""

    # --- Location editor ---
    @Slot('QVariant', result='QVariant')
    def createLocation(self, p):
        return self._rec("createLocation", _variant(p))

    @Slot('QVariant', result='QVariant')
    def updateLocation(self, p):
        return self._rec("updateLocation", _variant(p))

    # --- System editor ---
    @Slot('QVariant', result='QVariant')
    def createSystem(self, p):
        return self._rec("createSystem", _variant(p))

    @Slot('QVariant', result='QVariant')
    def updateSystem(self, p):
        return self._rec("updateSystem", _variant(p))

    # --- Asset editor ---
    @Slot('QVariant', result='QVariant')
    def createAsset(self, p):
        return self._rec("createAsset", _variant(p))

    @Slot('QVariant', result='QVariant')
    def updateAsset(self, p):
        return self._rec("updateAsset", _variant(p))

    # --- Component editor ---
    @Slot('QVariant', result='QVariant')
    def createComponent(self, p):
        return self._rec("createComponent", _variant(p))

    @Slot('QVariant', result='QVariant')
    def updateComponent(self, p):
        return self._rec("updateComponent", _variant(p))

    # --- Work request editor ---
    @Slot('QVariant', result='QVariant')
    def createWorkRequest(self, p):
        return self._rec("createWorkRequest", _variant(p))

    @Slot('QVariant', result='QVariant')
    def updateWorkRequest(self, p):
        return self._rec("updateWorkRequest", _variant(p))

    # --- Work order editor ---
    @Slot('QVariant', result='QVariant')
    def createWorkOrder(self, p):
        return self._rec("createWorkOrder", _variant(p))

    @Slot('QVariant', result='QVariant')
    def updateWorkOrder(self, p):
        return self._rec("updateWorkOrder", _variant(p))


def test_assets_dialog_host_edit_location_submit_button_emits_update() -> None:
    mock = _MockController()
    _, root = _load_host(
        ASSETS_DIALOG_HOST,
        {
            "workspaceController": mock,
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "parentLocationOptions": [{"value": "", "label": "None"}],
            "statusOptions": [{"value": "ACTIVE", "label": "Active"}],
            "criticalityOptions": [{"value": "MEDIUM", "label": "Medium"}],
        },
    )
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

    assert mock.count("updateLocation") == 1
    payload = mock.last("updateLocation")
    assert payload["locationId"] == "LOC-1"
    assert payload["locationCode"] == "LOC-100"
    assert payload["expectedVersion"] == 3.0


def test_work_request_dialog_host_edit_submit_button_emits_update() -> None:
    mock = _MockController()
    _, root = _load_host(
        WORK_REQUESTS_DIALOG_HOST,
        {
            "workspaceController": mock,
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "sourceTypeOptions": [{"value": "MANUAL", "label": "Manual"}],
            "priorityOptions": [{"value": "HIGH", "label": "High"}],
            "statusOptions": [
                {"value": "NEW", "label": "New"},
                {"value": "TRIAGED", "label": "Triaged"},
            ],
        },
    )
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

    assert mock.count("updateWorkRequest") == 1
    payload = mock.last("updateWorkRequest")
    assert payload["workRequestId"] == "WR-1"
    assert payload["requestType"] == "CORRECTIVE"
    assert payload["title"] == "Seal leak on transfer pump"
    assert payload["expectedVersion"] == 2.0


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
    mock = _MockController()
    _, root = _load_host(
        WORK_ORDERS_DIALOG_HOST,
        {
            "workspaceController": mock,
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "sourceTypeOptions": [{"value": "MANUAL", "label": "Manual"}],
            "workOrderTypeOptions": [{"value": "CORRECTIVE", "label": "Corrective"}],
            "priorityOptions": [{"value": "HIGH", "label": "High"}],
            "vendorOptions": [{"value": "", "label": "None"}],
        },
    )

    assert QMetaObject.invokeMethod(root, "openCreateDialog")
    dialog = _find_child(root, "workOrderEditorDialog")
    cancel_button = _find_child(dialog, "dialogCancelButton")
    assert QMetaObject.invokeMethod(cancel_button, "click")

    assert mock.calls == []

