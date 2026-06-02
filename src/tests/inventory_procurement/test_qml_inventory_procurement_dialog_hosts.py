from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Q_ARG, Property, QObject, QMetaObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml


INVENTORY_DIALOG_HOST = Path(
    "src/ui_qml/modules/inventory_procurement/qml/workspaces/inventory/InventoryDialogHost.qml"
)
CATALOG_DIALOG_HOST = Path(
    "src/ui_qml/modules/inventory_procurement/qml/workspaces/catalog/CatalogDialogHost.qml"
)
PROCUREMENT_DIALOG_HOST = Path(
    "src/ui_qml/modules/inventory_procurement/qml/workspaces/procurement/ProcurementDialogHost.qml"
)
RESERVATIONS_DIALOG_HOST = Path(
    "src/ui_qml/modules/inventory_procurement/qml/workspaces/reservations/ReservationsDialogHost.qml"
)


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["inventory-dialog-host-test"])


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


def _set_text(child: QObject, value: str) -> None:
    assert child.setProperty("text", value)


class _MockController(QObject):
    """Records the controller calls the dialog hosts make and returns success.

    The refactored hosts no longer emit ``*Requested`` signals; instead each
    ``onSubmitted``/``onAccepted`` handler calls
    ``root.workspaceController.<method>(payload)`` directly and (for most dialogs)
    passes the result to ``_handleResult`` which closes the dialog when
    ``result.ok !== false``. This mock returns ``{"ok": True}`` for every method
    so the dialog closes, while recording the call for assertion.
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

    # --- Inventory: storeroom editor ---
    @Slot('QVariant', result='QVariant')
    def createStoreroom(self, p):
        return self._rec("createStoreroom", _variant(p))

    @Slot('QVariant', result='QVariant')
    def updateStoreroom(self, p):
        return self._rec("updateStoreroom", _variant(p))

    # --- Inventory: stock movements ---
    @Slot('QVariant', result='QVariant')
    def postOpeningBalance(self, p):
        return self._rec("postOpeningBalance", _variant(p))

    @Slot('QVariant', result='QVariant')
    def postAdjustment(self, p):
        return self._rec("postAdjustment", _variant(p))

    @Slot('QVariant', result='QVariant')
    def issueStock(self, p):
        return self._rec("issueStock", _variant(p))

    @Slot('QVariant', result='QVariant')
    def returnStock(self, p):
        return self._rec("returnStock", _variant(p))

    @Slot('QVariant', result='QVariant')
    def transferStock(self, p):
        return self._rec("transferStock", _variant(p))

    # --- Catalog: categories / items / documents ---
    @Slot('QVariant', result='QVariant')
    def createCategory(self, p):
        return self._rec("createCategory", _variant(p))

    @Slot('QVariant', result='QVariant')
    def updateCategory(self, p):
        return self._rec("updateCategory", _variant(p))

    @Slot('QVariant', result='QVariant')
    def createItem(self, p):
        return self._rec("createItem", _variant(p))

    @Slot('QVariant', result='QVariant')
    def updateItem(self, p):
        return self._rec("updateItem", _variant(p))

    @Slot(str, str, result='QVariant')
    def linkDocument(self, item_id, document_id):
        return self._rec("linkDocument", (str(item_id), str(document_id)))

    # --- Procurement: requisitions / purchase orders / receipts ---
    @Slot('QVariant', result='QVariant')
    def createRequisition(self, p):
        return self._rec("createRequisition", _variant(p))

    @Slot('QVariant', result='QVariant')
    def updateRequisition(self, p):
        return self._rec("updateRequisition", _variant(p))

    @Slot('QVariant', result='QVariant')
    def addRequisitionLine(self, p):
        return self._rec("addRequisitionLine", _variant(p))

    @Slot('QVariant', result='QVariant')
    def createPurchaseOrder(self, p):
        return self._rec("createPurchaseOrder", _variant(p))

    @Slot('QVariant', result='QVariant')
    def updatePurchaseOrder(self, p):
        return self._rec("updatePurchaseOrder", _variant(p))

    @Slot('QVariant', result='QVariant')
    def addPurchaseOrderLine(self, p):
        return self._rec("addPurchaseOrderLine", _variant(p))

    @Slot('QVariant', result='QVariant')
    def postReceipt(self, p):
        return self._rec("postReceipt", _variant(p))

    # --- Reservations ---
    @Slot('QVariant', result='QVariant')
    def createReservation(self, p):
        return self._rec("createReservation", _variant(p))

    @Slot('QVariant', result='QVariant')
    def issueReservation(self, p):
        return self._rec("issueReservation", _variant(p))

    @Slot(str, result='QVariant')
    def releaseReservation(self, rid):
        return self._rec("releaseReservation", str(rid))

    @Slot(str, result='QVariant')
    def cancelReservation(self, rid):
        return self._rec("cancelReservation", str(rid))


def test_inventory_dialog_host_edit_storeroom_submit_button_emits_update() -> None:
    mock = _MockController()
    _, root = _load_host(
        INVENTORY_DIALOG_HOST,
        {
            "workspaceController": mock,
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "storeroomStatusOptions": [{"value": "ACTIVE", "label": "Active"}],
            "managerPartyOptions": [{"value": "PARTY-1", "label": "Manager Party"}],
        },
    )
    record = {
        "state": {
            "storeroomId": "ST-1",
            "version": 6,
            "storeroomCode": "MAIN",
            "name": "Main Storeroom",
            "siteId": "SITE-1",
            "status": "ACTIVE",
        }
    }

    assert QMetaObject.invokeMethod(root, "openEditStoreroomDialog", Q_ARG("QVariant", record))
    dialog = _find_child(root, "storeroomEditorDialog")
    _find_child(dialog, "dialogCancelButton")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(dialog, "populateFromStoreroom")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert mock.count("updateStoreroom") == 1
    payload = mock.last("updateStoreroom")
    assert payload["storeroomId"] == "ST-1"
    assert payload["storeroomCode"] == "MAIN"
    assert payload["expectedVersion"] == 6


def test_inventory_dialog_host_issue_stock_submit_button_emits_issue() -> None:
    mock = _MockController()
    _, root = _load_host(
        INVENTORY_DIALOG_HOST,
        {
            "workspaceController": mock,
            "itemOptions": [{"value": "ITEM-1", "label": "ITEM-1 - Filter"}],
            "storeroomOptions": [{"value": "ST-1", "label": "ST-1 - Main Storeroom"}],
        },
    )
    balance = {
        "state": {
            "stockItemId": "ITEM-1",
            "storeroomId": "ST-1",
            "uom": "EA",
            "averageCost": "8.50",
        }
    }

    assert QMetaObject.invokeMethod(root, "openIssueDialog", Q_ARG("QVariant", balance))
    dialog = _find_child(root, "stockMovementDialog")
    quantity_field = _find_child(dialog, "quantityField")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(dialog, "populateFromMovement")
    _set_text(quantity_field, "2.500")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert mock.count("issueStock") == 1
    payload = mock.last("issueStock")
    assert payload["stockItemId"] == "ITEM-1"
    assert payload["storeroomId"] == "ST-1"
    assert payload["quantity"] == "2.500"
    assert payload["direction"] == "DECREASE"
    assert payload["referenceType"] == "issue"


def test_catalog_dialog_host_link_document_submit_button_emits_link_request() -> None:
    mock = _MockController()
    _, root = _load_host(
        CATALOG_DIALOG_HOST,
        {
            "workspaceController": mock,
            "availableDocuments": [
                {"value": "DOC-2", "label": "DOC-2 - Spec"},
                {"value": "DOC-3", "label": "DOC-3 - SOP"},
            ],
        },
    )
    item = {
        "state": {"itemId": "ITEM-1"},
        "linkedDocuments": [{"value": "DOC-1", "label": "DOC-1 - Existing"}],
    }

    assert QMetaObject.invokeMethod(root, "openLinkDocumentDialog", Q_ARG("QVariant", item))
    dialog = _find_child(root, "documentLinkDialog")
    _find_child(dialog, "dialogCancelButton")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert mock.count("linkDocument") == 1
    assert mock.last("linkDocument") == ("ITEM-1", "DOC-2")


def test_procurement_dialog_host_edit_purchase_order_submit_button_emits_update() -> None:
    mock = _MockController()
    _, root = _load_host(
        PROCUREMENT_DIALOG_HOST,
        {
            "workspaceController": mock,
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "supplierOptions": [{"value": "SUP-1", "label": "SUP-1 - Supplier"}],
            "requisitionOptions": [{"value": "REQ-1", "label": "REQ-1 - Demand"}],
        },
    )
    record = {
        "state": {
            "purchaseOrderId": "PO-1",
            "version": 5,
            "siteId": "SITE-1",
            "supplierPartyId": "SUP-1",
            "sourceRequisitionId": "REQ-1",
            "currencyCode": "EUR",
        }
    }

    assert QMetaObject.invokeMethod(
        root, "openEditPurchaseOrderDialog", Q_ARG("QVariant", record)
    )
    dialog = _find_child(root, "purchaseOrderEditorDialog")
    _find_child(dialog, "dialogCancelButton")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(dialog, "populateFromPurchaseOrder")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert mock.count("updatePurchaseOrder") == 1
    payload = mock.last("updatePurchaseOrder")
    assert payload["purchaseOrderId"] == "PO-1"
    assert payload["supplierPartyId"] == "SUP-1"
    assert payload["sourceRequisitionId"] == "REQ-1"
    assert payload["expectedVersion"] == 5


def test_procurement_dialog_host_add_requisition_line_submit_button_emits_add() -> None:
    mock = _MockController()
    _, root = _load_host(
        PROCUREMENT_DIALOG_HOST,
        {
            "workspaceController": mock,
            "itemOptions": [{"value": "ITEM-1", "label": "ITEM-1 - Bearing"}],
            "supplierOptions": [{"value": "SUP-1", "label": "SUP-1 - Supplier"}],
        },
    )
    requisition = {"state": {"requisitionId": "REQ-1"}}

    assert QMetaObject.invokeMethod(
        root, "openRequisitionLineDialog", Q_ARG("QVariant", requisition)
    )
    dialog = _find_child(root, "requisitionLineDialog")
    quantity_field = _find_child(dialog, "quantityField")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(dialog, "populateFromTarget")
    _set_text(quantity_field, "5.000")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert mock.count("addRequisitionLine") == 1
    payload = mock.last("addRequisitionLine")
    assert payload["requisitionId"] == "REQ-1"
    assert payload["stockItemId"] == "ITEM-1"
    assert payload["quantityRequested"] == "5.000"


def test_procurement_dialog_host_cancel_button_does_not_emit_create() -> None:
    mock = _MockController()
    _, root = _load_host(
        PROCUREMENT_DIALOG_HOST,
        {
            "workspaceController": mock,
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "storeroomOptions": [{"value": "ST-1", "label": "ST-1 - Main Storeroom"}],
        },
    )

    assert QMetaObject.invokeMethod(
        root,
        "openCreateRequisitionDialog",
        Q_ARG("QVariant", "SITE-1"),
        Q_ARG("QVariant", "ST-1"),
    )
    dialog = _find_child(root, "requisitionEditorDialog")
    cancel_button = _find_child(dialog, "dialogCancelButton")
    assert QMetaObject.invokeMethod(cancel_button, "click")

    assert mock.calls == []


def test_reservations_dialog_host_create_submit_button_emits_create() -> None:
    mock = _MockController()
    _, root = _load_host(
        RESERVATIONS_DIALOG_HOST,
        {
            "workspaceController": mock,
            "itemOptions": [{"value": "ITEM-1", "label": "ITEM-1 - Bearing"}],
            "storeroomOptions": [{"value": "ST-1", "label": "ST-1 - Main Storeroom"}],
        },
    )

    assert QMetaObject.invokeMethod(
        root,
        "openCreateReservationDialog",
        Q_ARG("QVariant", "ITEM-1"),
        Q_ARG("QVariant", "ST-1"),
    )
    dialog = _find_child(root, "reservationCreateDialog")
    quantity_field = _find_child(dialog, "quantityField")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(dialog, "populateFromReservation")
    _set_text(quantity_field, "3.000")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert mock.count("createReservation") == 1
    payload = mock.last("createReservation")
    assert payload["stockItemId"] == "ITEM-1"
    assert payload["storeroomId"] == "ST-1"
    assert payload["reservedQty"] == "3.000"


def test_reservations_dialog_host_issue_submit_button_emits_issue() -> None:
    mock = _MockController()
    _, root = _load_host(RESERVATIONS_DIALOG_HOST, {"workspaceController": mock})
    reservation = {
        "title": "RSV-1",
        "state": {
            "reservationId": "RSV-1",
            "remainingQty": "4.000",
            "remainingQtyLabel": "4.000 EA",
        },
    }

    assert QMetaObject.invokeMethod(
        root, "openIssueReservationDialog", Q_ARG("QVariant", reservation)
    )
    dialog = _find_child(root, "reservationIssueDialog")
    _find_child(dialog, "dialogCancelButton")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(dialog, "populateFromReservation")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert mock.count("issueReservation") == 1
    payload = mock.last("issueReservation")
    assert payload["reservationId"] == "RSV-1"
    assert payload["quantity"] == "4.000"


def test_reservations_dialog_host_release_confirmation_submit_button_emits_release() -> None:
    mock = _MockController()
    _, root = _load_host(RESERVATIONS_DIALOG_HOST, {"workspaceController": mock})
    reservation = {"state": {"reservationId": "RSV-1"}}

    assert QMetaObject.invokeMethod(
        root, "openReleaseConfirmation", Q_ARG("QVariant", reservation)
    )
    dialog = _find_child(root, "reservationConfirmationDialog")
    _find_child(dialog, "dialogCancelButton")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert mock.count("releaseReservation") == 1
    assert mock.last("releaseReservation") == "RSV-1"

