from __future__ import annotations

from PySide6.QtWidgets import QDialog, QMessageBox

from core.modules.inventory_procurement.services.inventory.service import InventoryService
from core.modules.inventory_procurement.services.item_master.service import ItemMasterService
from core.modules.inventory_procurement.services.procurement.purchasing_service import PurchasingService
from core.modules.inventory_procurement.services.procurement.service import ProcurementService
from core.modules.inventory_procurement.services.reference_service import InventoryReferenceService
from core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from ui.modules.inventory_procurement.procurement.procurement_dialogs import (
    PurchaseOrderEditDialog,
    PurchaseOrderLineDialog,
)
from ui.modules.inventory_procurement.shared.procurement_support import (
    build_item_lookup,
    build_requisition_lookup,
    build_storeroom_lookup,
)
from ui.modules.inventory_procurement.shared.reference_support import (
    build_option_rows,
    build_party_lookup,
    build_site_lookup,
    format_party_label,
    format_site_label,
)


class PurchaseOrdersActionsMixin:
    _purchasing_service: PurchasingService
    _item_service: ItemMasterService
    _reference_service: InventoryReferenceService
    _procurement_service: ProcurementService
    _inventory_service: InventoryService

    def reload_purchase_orders(self) -> None:
        selected_id = self._selected_purchase_order_id()
        try:
            sites = self._reference_service.list_sites(active_only=None)
            storerooms = self._inventory_service.list_storerooms(active_only=None)
            items = self._item_service.list_items(active_only=None)
            parties = self._reference_service.list_business_parties(active_only=None)
            requisitions = self._procurement_service.list_requisitions()
            self._site_lookup = build_site_lookup(sites)
            self._storeroom_lookup = build_storeroom_lookup(storerooms)
            self._item_lookup = build_item_lookup(items)
            self._party_lookup = build_party_lookup(parties)
            self._requisition_lookup = build_requisition_lookup(requisitions)
            self._reload_site_filter()
            self._reload_supplier_filter()
            rows = self._purchasing_service.list_purchase_orders(
                status=self._selected_status_filter(),
                site_id=self._selected_site_filter(),
                supplier_party_id=self._selected_supplier_filter(),
            )
            self._rows = self._apply_search_filter(rows)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            self._rows = []
            self._selected_lines = []
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to load purchase orders: {exc}")
            self._rows = []
            self._selected_lines = []
        self._populate_table(selected_id=selected_id)
        self._update_badges()
        self._sync_actions()

    def create_purchase_order(self) -> None:
        if not self._can_manage:
            return
        dialog = PurchaseOrderEditDialog(
            site_options=build_option_rows(
                {site_id: format_site_label(site_id, self._site_lookup) for site_id in self._site_lookup}
            ),
            supplier_options=build_option_rows(
                {party_id: format_party_label(party_id, self._party_lookup) for party_id in self._party_lookup}
            ),
            requisition_options=self._requisition_options(),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            purchase_order = self._purchasing_service.create_purchase_order(
                site_id=dialog.site_id,
                supplier_party_id=dialog.supplier_party_id,
                currency_code=dialog.currency_code or None,
                source_requisition_id=dialog.source_requisition_id,
                expected_delivery_date=dialog.expected_delivery_date,
                supplier_reference=dialog.supplier_reference,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to create purchase order: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def edit_purchase_order(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        dialog = PurchaseOrderEditDialog(
            site_options=build_option_rows(
                {site_id: format_site_label(site_id, self._site_lookup) for site_id in self._site_lookup}
            ),
            supplier_options=build_option_rows(
                {party_id: format_party_label(party_id, self._party_lookup) for party_id in self._party_lookup}
            ),
            requisition_options=self._requisition_options(),
            purchase_order=purchase_order,
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._purchasing_service.update_purchase_order(
                purchase_order.id,
                site_id=dialog.site_id,
                supplier_party_id=dialog.supplier_party_id,
                currency_code=dialog.currency_code or None,
                source_requisition_id=dialog.source_requisition_id,
                expected_delivery_date=dialog.expected_delivery_date,
                supplier_reference=dialog.supplier_reference,
                notes=dialog.notes,
                expected_version=purchase_order.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_purchase_orders()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to update purchase order: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def add_line(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        dialog = PurchaseOrderLineDialog(
            item_options=self._active_item_options(),
            storeroom_options=self._storeroom_options_for_site(purchase_order.site_id),
            requisition_line_options=self._requisition_line_options(purchase_order.source_requisition_id),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._purchasing_service.add_purchase_order_line(
                purchase_order.id,
                stock_item_id=dialog.stock_item_id,
                destination_storeroom_id=dialog.destination_storeroom_id,
                quantity_ordered=dialog.quantity_ordered,
                unit_price=dialog.unit_price,
                expected_delivery_date=dialog.expected_delivery_date,
                description=dialog.description,
                source_requisition_line_id=dialog.source_requisition_line_id,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to add purchase-order line: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def submit_purchase_order(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Submit Purchase Order",
            f"Submit {purchase_order.po_number} for approval?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._purchasing_service.submit_purchase_order(purchase_order.id)
        except ValidationError as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to submit purchase order: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def cancel_purchase_order(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Cancel Purchase Order",
            f"Cancel draft purchase order {purchase_order.po_number}?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._purchasing_service.cancel_purchase_order(
                purchase_order.id,
                expected_version=purchase_order.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_purchase_orders()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to cancel purchase order: {exc}")
            return
        self.reload_purchase_orders()

    def send_purchase_order(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Send Purchase Order",
            f"Mark purchase order {purchase_order.po_number} as sent to the supplier?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._purchasing_service.send_purchase_order(purchase_order.id)
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_purchase_orders()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to send purchase order: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def close_purchase_order(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Close Purchase Order",
            f"Close purchase order {purchase_order.po_number}? This is only allowed once all line quantities are fully processed.",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._purchasing_service.close_purchase_order(purchase_order.id)
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_purchase_orders()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to close purchase order: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def _on_inventory_changed(self, _entity_id: str) -> None:
        self.reload_purchase_orders()
