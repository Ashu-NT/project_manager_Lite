from __future__ import annotations

from PySide6.QtWidgets import QDialog, QMessageBox

from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from ui.modules.inventory_procurement.procurement.procurement_dialogs import (
    RequisitionEditDialog,
    RequisitionLineDialog,
)
from ui.modules.inventory_procurement.shared.procurement_support import build_item_lookup, build_storeroom_lookup
from ui.modules.inventory_procurement.shared.reference_support import (
    build_option_rows,
    build_party_lookup,
    build_site_lookup,
    format_party_label,
    format_site_label,
)


class RequisitionsActionsMixin:
    def reload_requisitions(self) -> None:
        selected_id = self._selected_requisition_id()
        try:
            sites = self._reference_service.list_sites(active_only=None)
            storerooms = self._inventory_service.list_storerooms(active_only=None)
            items = self._item_service.list_items(active_only=None)
            parties = self._reference_service.list_business_parties(active_only=None)
            self._site_lookup = build_site_lookup(sites)
            self._storeroom_lookup = build_storeroom_lookup(storerooms)
            self._item_lookup = build_item_lookup(items)
            self._party_lookup = build_party_lookup(parties)
            self._reload_site_filter()
            self._reload_storeroom_filter()
            rows = self._procurement_service.list_requisitions(
                status=self._selected_status_filter(),
                site_id=self._selected_site_filter(),
                storeroom_id=self._selected_storeroom_filter(),
            )
            self._rows = self._apply_search_filter(rows)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Requisitions", str(exc))
            self._rows = []
            self._selected_lines = []
            self._site_lookup = {}
            self._storeroom_lookup = {}
            self._item_lookup = {}
            self._party_lookup = {}
        except Exception as exc:
            QMessageBox.critical(self, "Requisitions", f"Failed to load requisitions: {exc}")
            self._rows = []
            self._selected_lines = []
            self._site_lookup = {}
            self._storeroom_lookup = {}
            self._item_lookup = {}
            self._party_lookup = {}
        self._populate_table(selected_id=selected_id)
        self._update_badges()
        self._sync_actions()

    def create_requisition(self) -> None:
        if not self._can_manage:
            return
        dialog = RequisitionEditDialog(
            site_options=build_option_rows(
                {site_id: format_site_label(site_id, self._site_lookup) for site_id in self._site_lookup}
            ),
            storeroom_options=self._storeroom_option_rows(),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            requisition = self._procurement_service.create_requisition(
                requesting_site_id=dialog.site_id,
                requesting_storeroom_id=dialog.storeroom_id,
                purpose=dialog.purpose,
                needed_by_date=dialog.needed_by_date,
                priority=dialog.priority,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Requisitions", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Requisitions", f"Failed to create requisition: {exc}")
            return
        self.reload_requisitions()
        self._select_requisition(requisition.id)

    def edit_requisition(self) -> None:
        requisition = self._selected_requisition()
        if requisition is None or not self._can_manage:
            return
        dialog = RequisitionEditDialog(
            site_options=build_option_rows(
                {site_id: format_site_label(site_id, self._site_lookup) for site_id in self._site_lookup}
            ),
            storeroom_options=self._storeroom_option_rows(),
            requisition=requisition,
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._procurement_service.update_requisition(
                requisition.id,
                requesting_site_id=dialog.site_id,
                requesting_storeroom_id=dialog.storeroom_id,
                purpose=dialog.purpose,
                needed_by_date=dialog.needed_by_date,
                priority=dialog.priority,
                notes=dialog.notes,
                expected_version=requisition.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Requisitions", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_requisitions()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Requisitions", f"Failed to update requisition: {exc}")
            return
        self.reload_requisitions()
        self._select_requisition(requisition.id)

    def add_line(self) -> None:
        requisition = self._selected_requisition()
        if requisition is None or not self._can_manage:
            return
        dialog = RequisitionLineDialog(
            item_options=self._active_item_options(),
            supplier_options=build_option_rows(
                {party_id: format_party_label(party_id, self._party_lookup) for party_id in self._party_lookup},
                include_blank=False,
            ),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._procurement_service.add_requisition_line(
                requisition.id,
                stock_item_id=dialog.stock_item_id,
                quantity_requested=dialog.quantity_requested,
                description=dialog.description,
                needed_by_date=dialog.needed_by_date,
                estimated_unit_cost=dialog.estimated_unit_cost,
                suggested_supplier_party_id=dialog.suggested_supplier_party_id,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Requisitions", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Requisitions", f"Failed to add requisition line: {exc}")
            return
        self.reload_requisitions()
        self._select_requisition(requisition.id)

    def submit_requisition(self) -> None:
        requisition = self._selected_requisition()
        if requisition is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Submit Requisition",
            f"Submit {requisition.requisition_number} for approval?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._procurement_service.submit_requisition(requisition.id)
        except ValidationError as exc:
            QMessageBox.warning(self, "Requisitions", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Requisitions", f"Failed to submit requisition: {exc}")
            return
        self.reload_requisitions()
        self._select_requisition(requisition.id)

    def cancel_requisition(self) -> None:
        requisition = self._selected_requisition()
        if requisition is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Cancel Requisition",
            f"Cancel draft requisition {requisition.requisition_number}?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._procurement_service.cancel_requisition(
                requisition.id,
                expected_version=requisition.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Requisitions", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_requisitions()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Requisitions", f"Failed to cancel requisition: {exc}")
            return
        self.reload_requisitions()

    def _on_inventory_changed(self, _entity_id: str) -> None:
        self.reload_requisitions()
