from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Q_ARG, QObject, QMetaObject
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


def test_inventory_dialog_host_edit_storeroom_submit_button_emits_update() -> None:
    _, root = _load_host(
        INVENTORY_DIALOG_HOST,
        {
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "storeroomStatusOptions": [{"value": "ACTIVE", "label": "Active"}],
            "managerPartyOptions": [{"value": "PARTY-1", "label": "Manager Party"}],
        },
    )
    captured: list[dict] = []
    root.updateStoreroomRequested.connect(lambda payload: captured.append(_variant(payload)))
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

    assert len(captured) == 1
    assert captured[0]["storeroomId"] == "ST-1"
    assert captured[0]["storeroomCode"] == "MAIN"
    assert captured[0]["expectedVersion"] == 6


def test_inventory_dialog_host_issue_stock_submit_button_emits_issue() -> None:
    _, root = _load_host(
        INVENTORY_DIALOG_HOST,
        {
            "itemOptions": [{"value": "ITEM-1", "label": "ITEM-1 - Filter"}],
            "storeroomOptions": [{"value": "ST-1", "label": "ST-1 - Main Storeroom"}],
        },
    )
    captured: list[dict] = []
    root.issueStockRequested.connect(lambda payload: captured.append(_variant(payload)))
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

    assert len(captured) == 1
    assert captured[0]["stockItemId"] == "ITEM-1"
    assert captured[0]["storeroomId"] == "ST-1"
    assert captured[0]["quantity"] == "2.500"
    assert captured[0]["direction"] == "DECREASE"
    assert captured[0]["referenceType"] == "issue"


def test_catalog_dialog_host_link_document_submit_button_emits_link_request() -> None:
    _, root = _load_host(
        CATALOG_DIALOG_HOST,
        {
            "availableDocuments": [
                {"value": "DOC-2", "label": "DOC-2 - Spec"},
                {"value": "DOC-3", "label": "DOC-3 - SOP"},
            ]
        },
    )
    captured: list[tuple[str, str]] = []
    root.linkDocumentRequested.connect(
        lambda item_id, document_id: captured.append((str(item_id), str(document_id)))
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

    assert captured == [("ITEM-1", "DOC-2")]


def test_procurement_dialog_host_edit_purchase_order_submit_button_emits_update() -> None:
    _, root = _load_host(
        PROCUREMENT_DIALOG_HOST,
        {
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "supplierOptions": [{"value": "SUP-1", "label": "SUP-1 - Supplier"}],
            "requisitionOptions": [{"value": "REQ-1", "label": "REQ-1 - Demand"}],
        },
    )
    captured: list[dict] = []
    root.updatePurchaseOrderRequested.connect(
        lambda payload: captured.append(_variant(payload))
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

    assert len(captured) == 1
    assert captured[0]["purchaseOrderId"] == "PO-1"
    assert captured[0]["supplierPartyId"] == "SUP-1"
    assert captured[0]["sourceRequisitionId"] == "REQ-1"
    assert captured[0]["expectedVersion"] == 5


def test_procurement_dialog_host_add_requisition_line_submit_button_emits_add() -> None:
    _, root = _load_host(
        PROCUREMENT_DIALOG_HOST,
        {
            "itemOptions": [{"value": "ITEM-1", "label": "ITEM-1 - Bearing"}],
            "supplierOptions": [{"value": "SUP-1", "label": "SUP-1 - Supplier"}],
        },
    )
    captured: list[dict] = []
    root.addRequisitionLineRequested.connect(lambda payload: captured.append(_variant(payload)))
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

    assert len(captured) == 1
    assert captured[0]["requisitionId"] == "REQ-1"
    assert captured[0]["stockItemId"] == "ITEM-1"
    assert captured[0]["quantityRequested"] == "5.000"


def test_procurement_dialog_host_cancel_button_does_not_emit_create() -> None:
    _, root = _load_host(
        PROCUREMENT_DIALOG_HOST,
        {
            "siteOptions": [{"value": "SITE-1", "label": "SITE-1 - Main Site"}],
            "storeroomOptions": [{"value": "ST-1", "label": "ST-1 - Main Storeroom"}],
        },
    )
    created: list[dict] = []
    root.createRequisitionRequested.connect(lambda payload: created.append(_variant(payload)))

    assert QMetaObject.invokeMethod(
        root,
        "openCreateRequisitionDialog",
        Q_ARG("QVariant", "SITE-1"),
        Q_ARG("QVariant", "ST-1"),
    )
    dialog = _find_child(root, "requisitionEditorDialog")
    cancel_button = _find_child(dialog, "dialogCancelButton")
    assert QMetaObject.invokeMethod(cancel_button, "click")

    assert created == []


def test_reservations_dialog_host_create_submit_button_emits_create() -> None:
    _, root = _load_host(
        RESERVATIONS_DIALOG_HOST,
        {
            "itemOptions": [{"value": "ITEM-1", "label": "ITEM-1 - Bearing"}],
            "storeroomOptions": [{"value": "ST-1", "label": "ST-1 - Main Storeroom"}],
        },
    )
    captured: list[dict] = []
    root.createReservationRequested.connect(lambda payload: captured.append(_variant(payload)))

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

    assert len(captured) == 1
    assert captured[0]["stockItemId"] == "ITEM-1"
    assert captured[0]["storeroomId"] == "ST-1"
    assert captured[0]["reservedQty"] == "3.000"


def test_reservations_dialog_host_issue_submit_button_emits_issue() -> None:
    _, root = _load_host(RESERVATIONS_DIALOG_HOST, {})
    captured: list[dict] = []
    root.issueReservationRequested.connect(lambda payload: captured.append(_variant(payload)))
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

    assert len(captured) == 1
    assert captured[0]["reservationId"] == "RSV-1"
    assert captured[0]["quantity"] == "4.000"


def test_reservations_dialog_host_release_confirmation_submit_button_emits_release() -> None:
    _, root = _load_host(RESERVATIONS_DIALOG_HOST, {})
    captured: list[str] = []
    root.releaseReservationRequested.connect(lambda reservation_id: captured.append(str(reservation_id)))
    reservation = {"state": {"reservationId": "RSV-1"}}

    assert QMetaObject.invokeMethod(
        root, "openReleaseConfirmation", Q_ARG("QVariant", reservation)
    )
    dialog = _find_child(root, "reservationConfirmationDialog")
    _find_child(dialog, "dialogCancelButton")
    submit_button = _find_child(dialog, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert captured == ["RSV-1"]
