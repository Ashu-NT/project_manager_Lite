from __future__ import annotations

from datetime import date
from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementProcurementDesktopApi,
    InventoryPurchaseOrderCreateCommand,
    InventoryPurchaseOrderLineCreateCommand,
    InventoryPurchaseOrderUpdateCommand,
    InventoryReceiptLineCommand,
    InventoryReceiptPostCommand,
    InventoryRequisitionCreateCommand,
    InventoryRequisitionLineCreateCommand,
    InventoryRequisitionUpdateCommand,
    build_inventory_procurement_procurement_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryCatalogOverviewViewModel,
    InventoryDetailFieldViewModel,
    InventoryDetailViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.procurement import (
    InventoryProcurementProcurementWorkspaceViewModel,
)


class InventoryProcurementProcurementWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: InventoryProcurementProcurementDesktopApi | None = None,
    ) -> None:
        self._desktop_api = (
            desktop_api or build_inventory_procurement_procurement_desktop_api()
        )

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        site_filter: str = "all",
        storeroom_filter: str = "all",
        supplier_filter: str = "all",
        requisition_status_filter: str = "all",
        purchase_order_status_filter: str = "all",
        selected_requisition_id: str | None = None,
        selected_purchase_order_id: str | None = None,
    ) -> InventoryProcurementProcurementWorkspaceViewModel:
        site_options = (
            InventorySelectorOptionViewModel(value="all", label="All sites"),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_site_options(active_only=None)
            ),
        )
        storeroom_options = (
            InventorySelectorOptionViewModel(value="all", label="All storerooms"),
            *(
                InventorySelectorOptionViewModel(
                    value=option.value,
                    label=f"{option.label} ({option.site_label})",
                )
                for option in self._desktop_api.list_storeroom_options(active_only=None)
            ),
        )
        supplier_options = (
            InventorySelectorOptionViewModel(value="all", label="All suppliers"),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_supplier_options(active_only=None)
            ),
        )
        requisition_status_options = (
            InventorySelectorOptionViewModel(value="all", label="All requisition statuses"),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_requisition_statuses()
            ),
        )
        purchase_order_status_options = (
            InventorySelectorOptionViewModel(
                value="all",
                label="All purchase-order statuses",
            ),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_purchase_order_statuses()
            ),
        )
        item_options = tuple(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_item_options(active_only=None)
        )

        normalized_search = (search_text or "").strip()
        normalized_site_filter = self._normalize_filter(site_filter, site_options)
        normalized_storeroom_filter = self._normalize_filter(
            storeroom_filter,
            storeroom_options,
        )
        normalized_supplier_filter = self._normalize_filter(
            supplier_filter,
            supplier_options,
        )
        normalized_requisition_status_filter = self._normalize_filter(
            requisition_status_filter,
            requisition_status_options,
        )
        normalized_purchase_order_status_filter = self._normalize_filter(
            purchase_order_status_filter,
            purchase_order_status_options,
        )

        all_requisitions = self._desktop_api.list_requisitions(limit=500)
        filtered_requisitions = tuple(
            row
            for row in self._desktop_api.list_requisitions(
                status=None
                if normalized_requisition_status_filter == "all"
                else normalized_requisition_status_filter,
                limit=500,
            )
            if self._requisition_matches(
                row,
                normalized_search,
                normalized_site_filter,
                normalized_storeroom_filter,
            )
        )

        all_purchase_orders = self._desktop_api.list_purchase_orders(limit=500)
        filtered_purchase_orders = tuple(
            row
            for row in self._desktop_api.list_purchase_orders(
                status=None
                if normalized_purchase_order_status_filter == "all"
                else normalized_purchase_order_status_filter,
                limit=500,
            )
            if self._purchase_order_matches(
                row,
                normalized_search,
                normalized_site_filter,
                normalized_supplier_filter,
            )
        )

        all_receipts = self._desktop_api.list_receipts(limit=500)

        resolved_selected_requisition_id = self._resolve_selected_id(
            selected_requisition_id,
            filtered_requisitions,
        )
        selected_requisition = next(
            (
                row
                for row in filtered_requisitions
                if row.id == resolved_selected_requisition_id
            ),
            None,
        )
        selected_requisition_lines = (
            self._desktop_api.list_requisition_lines(selected_requisition.id)
            if selected_requisition is not None
            else ()
        )

        resolved_selected_purchase_order_id = self._resolve_selected_id(
            selected_purchase_order_id,
            filtered_purchase_orders,
        )
        selected_purchase_order = next(
            (
                row
                for row in filtered_purchase_orders
                if row.id == resolved_selected_purchase_order_id
            ),
            None,
        )
        selected_purchase_order_lines = (
            self._desktop_api.list_purchase_order_lines(selected_purchase_order.id)
            if selected_purchase_order is not None
            else ()
        )
        selected_receipts = (
            self._desktop_api.list_receipts(
                purchase_order_id=selected_purchase_order.id,
                limit=200,
            )
            if selected_purchase_order is not None
            else ()
        )

        requisition_options = tuple(
            InventorySelectorOptionViewModel(
                value=row.id,
                label=(
                    f"{row.requisition_number} | {row.requesting_site_label} | "
                    f"{row.status_label}"
                ),
            )
            for row in all_requisitions
            if row.status in {"APPROVED", "PARTIALLY_SOURCED"}
        )
        requisition_line_options = self._build_requisition_line_options(
            selected_purchase_order.source_requisition_id
            if selected_purchase_order is not None
            else None
        )

        receipt_line_map = {
            receipt.id: self._desktop_api.list_receipt_lines(receipt.id)
            for receipt in selected_receipts
        }

        return InventoryProcurementProcurementWorkspaceViewModel(
            overview=self._build_overview(
                all_requisitions=all_requisitions,
                filtered_requisitions=filtered_requisitions,
                all_purchase_orders=all_purchase_orders,
                filtered_purchase_orders=filtered_purchase_orders,
                all_receipts=all_receipts,
            ),
            site_options=site_options,
            storeroom_options=storeroom_options,
            supplier_options=supplier_options,
            requisition_status_options=requisition_status_options,
            purchase_order_status_options=purchase_order_status_options,
            item_options=item_options,
            requisition_options=requisition_options,
            requisition_line_options=requisition_line_options,
            selected_site_filter=normalized_site_filter,
            selected_storeroom_filter=normalized_storeroom_filter,
            selected_supplier_filter=normalized_supplier_filter,
            selected_requisition_status_filter=normalized_requisition_status_filter,
            selected_purchase_order_status_filter=normalized_purchase_order_status_filter,
            search_text=normalized_search,
            requisitions=tuple(
                self._to_requisition_record_view_model(row)
                for row in filtered_requisitions
            ),
            selected_requisition_id=resolved_selected_requisition_id,
            selected_requisition_detail=self._build_requisition_detail(
                selected_requisition,
                selected_requisition_lines,
            ),
            requisition_lines=tuple(
                self._to_requisition_line_record_view_model(row)
                for row in selected_requisition_lines
            ),
            requisitions_empty_state=self._build_requisitions_empty_state(
                all_requisitions=all_requisitions,
                filtered_requisitions=filtered_requisitions,
                search_text=normalized_search,
                site_filter=normalized_site_filter,
                storeroom_filter=normalized_storeroom_filter,
                status_filter=normalized_requisition_status_filter,
            ),
            requisition_lines_empty_state=self._build_requisition_lines_empty_state(
                selected_requisition=selected_requisition,
                selected_requisition_lines=selected_requisition_lines,
            ),
            purchase_orders=tuple(
                self._to_purchase_order_record_view_model(row)
                for row in filtered_purchase_orders
            ),
            selected_purchase_order_id=resolved_selected_purchase_order_id,
            selected_purchase_order_detail=self._build_purchase_order_detail(
                selected_purchase_order,
                selected_purchase_order_lines,
            ),
            purchase_order_lines=tuple(
                self._to_purchase_order_line_record_view_model(row)
                for row in selected_purchase_order_lines
            ),
            purchase_orders_empty_state=self._build_purchase_orders_empty_state(
                all_purchase_orders=all_purchase_orders,
                filtered_purchase_orders=filtered_purchase_orders,
                search_text=normalized_search,
                site_filter=normalized_site_filter,
                supplier_filter=normalized_supplier_filter,
                status_filter=normalized_purchase_order_status_filter,
            ),
            purchase_order_lines_empty_state=self._build_purchase_order_lines_empty_state(
                selected_purchase_order=selected_purchase_order,
                selected_purchase_order_lines=selected_purchase_order_lines,
            ),
            receipts=tuple(
                self._to_receipt_record_view_model(
                    receipt,
                    receipt_line_map.get(receipt.id, ()),
                )
                for receipt in selected_receipts
            ),
            receipts_empty_state=self._build_receipts_empty_state(
                selected_purchase_order=selected_purchase_order,
                selected_receipts=selected_receipts,
            ),
            empty_state="",
        )

    def create_requisition(self, payload: dict[str, Any]) -> None:
        self._desktop_api.create_requisition(
            InventoryRequisitionCreateCommand(
                requesting_site_id=self._require_text(
                    payload,
                    "requestingSiteId",
                    "Choose a site before saving the requisition.",
                ),
                requesting_storeroom_id=self._require_text(
                    payload,
                    "requestingStoreroomId",
                    "Choose a storeroom before saving the requisition.",
                ),
                purpose=self._optional_text(payload, "purpose") or "",
                needed_by_date=self._optional_date(payload, "neededByDate"),
                priority=self._optional_text(payload, "priority") or "NORMAL",
                notes=self._optional_text(payload, "notes") or "",
            )
        )

    def update_requisition(self, payload: dict[str, Any]) -> None:
        self._desktop_api.update_requisition(
            InventoryRequisitionUpdateCommand(
                requisition_id=self._require_text(
                    payload,
                    "requisitionId",
                    "Select a requisition before editing it.",
                ),
                requesting_site_id=self._require_text(
                    payload,
                    "requestingSiteId",
                    "Choose a site before saving the requisition.",
                ),
                requesting_storeroom_id=self._require_text(
                    payload,
                    "requestingStoreroomId",
                    "Choose a storeroom before saving the requisition.",
                ),
                purpose=self._optional_text(payload, "purpose") or "",
                needed_by_date=self._optional_date(payload, "neededByDate"),
                priority=self._optional_text(payload, "priority") or "NORMAL",
                notes=self._optional_text(payload, "notes") or "",
                expected_version=self._optional_int(payload, "expectedVersion"),
            )
        )

    def add_requisition_line(self, payload: dict[str, Any]) -> None:
        self._desktop_api.add_requisition_line(
            InventoryRequisitionLineCreateCommand(
                requisition_id=self._require_text(
                    payload,
                    "requisitionId",
                    "Select a requisition before adding a line.",
                ),
                stock_item_id=self._require_text(
                    payload,
                    "stockItemId",
                    "Choose an item before adding a requisition line.",
                ),
                quantity_requested=self._require_positive_float(
                    payload,
                    "quantityRequested",
                    "Requested quantity must be greater than zero.",
                ),
                description=self._optional_text(payload, "description") or "",
                needed_by_date=self._optional_date(payload, "neededByDate"),
                estimated_unit_cost=self._optional_float(payload, "estimatedUnitCost")
                or 0.0,
                suggested_supplier_party_id=self._optional_text(
                    payload,
                    "suggestedSupplierPartyId",
                ),
                notes=self._optional_text(payload, "notes") or "",
            )
        )

    def submit_requisition(self, requisition_id: str) -> None:
        self._desktop_api.submit_requisition(
            self._require_identifier(
                requisition_id,
                "Select a requisition before submitting it.",
            )
        )

    def cancel_requisition(self, requisition_id: str) -> None:
        self._desktop_api.cancel_requisition(
            self._require_identifier(
                requisition_id,
                "Select a requisition before cancelling it.",
            )
        )

    def create_purchase_order(self, payload: dict[str, Any]) -> None:
        self._desktop_api.create_purchase_order(
            InventoryPurchaseOrderCreateCommand(
                site_id=self._require_text(
                    payload,
                    "siteId",
                    "Choose a site before saving the purchase order.",
                ),
                supplier_party_id=self._require_text(
                    payload,
                    "supplierPartyId",
                    "Choose a supplier before saving the purchase order.",
                ),
                currency_code=self._optional_text(payload, "currencyCode"),
                source_requisition_id=self._optional_text(payload, "sourceRequisitionId"),
                expected_delivery_date=self._optional_date(
                    payload,
                    "expectedDeliveryDate",
                ),
                supplier_reference=self._optional_text(payload, "supplierReference")
                or "",
                notes=self._optional_text(payload, "notes") or "",
            )
        )

    def update_purchase_order(self, payload: dict[str, Any]) -> None:
        self._desktop_api.update_purchase_order(
            InventoryPurchaseOrderUpdateCommand(
                purchase_order_id=self._require_text(
                    payload,
                    "purchaseOrderId",
                    "Select a purchase order before editing it.",
                ),
                site_id=self._require_text(
                    payload,
                    "siteId",
                    "Choose a site before saving the purchase order.",
                ),
                supplier_party_id=self._require_text(
                    payload,
                    "supplierPartyId",
                    "Choose a supplier before saving the purchase order.",
                ),
                currency_code=self._optional_text(payload, "currencyCode"),
                source_requisition_id=self._optional_text(payload, "sourceRequisitionId"),
                expected_delivery_date=self._optional_date(
                    payload,
                    "expectedDeliveryDate",
                ),
                supplier_reference=self._optional_text(payload, "supplierReference")
                or "",
                notes=self._optional_text(payload, "notes") or "",
                expected_version=self._optional_int(payload, "expectedVersion"),
            )
        )

    def add_purchase_order_line(self, payload: dict[str, Any]) -> None:
        self._desktop_api.add_purchase_order_line(
            InventoryPurchaseOrderLineCreateCommand(
                purchase_order_id=self._require_text(
                    payload,
                    "purchaseOrderId",
                    "Select a purchase order before adding a line.",
                ),
                stock_item_id=self._require_text(
                    payload,
                    "stockItemId",
                    "Choose an item before adding a purchase-order line.",
                ),
                destination_storeroom_id=self._require_text(
                    payload,
                    "destinationStoreroomId",
                    "Choose a destination storeroom before adding a line.",
                ),
                quantity_ordered=self._require_positive_float(
                    payload,
                    "quantityOrdered",
                    "Ordered quantity must be greater than zero.",
                ),
                unit_price=self._optional_float(payload, "unitPrice") or 0.0,
                expected_delivery_date=self._optional_date(
                    payload,
                    "expectedDeliveryDate",
                ),
                description=self._optional_text(payload, "description") or "",
                source_requisition_line_id=self._optional_text(
                    payload,
                    "sourceRequisitionLineId",
                ),
                notes=self._optional_text(payload, "notes") or "",
            )
        )

    def submit_purchase_order(self, purchase_order_id: str) -> None:
        self._desktop_api.submit_purchase_order(
            self._require_identifier(
                purchase_order_id,
                "Select a purchase order before submitting it.",
            )
        )

    def send_purchase_order(self, purchase_order_id: str) -> None:
        self._desktop_api.send_purchase_order(
            self._require_identifier(
                purchase_order_id,
                "Select a purchase order before sending it.",
            )
        )

    def cancel_purchase_order(self, purchase_order_id: str) -> None:
        self._desktop_api.cancel_purchase_order(
            self._require_identifier(
                purchase_order_id,
                "Select a purchase order before cancelling it.",
            )
        )

    def close_purchase_order(self, purchase_order_id: str) -> None:
        self._desktop_api.close_purchase_order(
            self._require_identifier(
                purchase_order_id,
                "Select a purchase order before closing it.",
            )
        )

    def post_receipt(self, payload: dict[str, Any]) -> None:
        purchase_order_id = self._require_text(
            payload,
            "purchaseOrderId",
            "Select a purchase order before posting a receipt.",
        )
        raw_lines = payload.get("receiptLines", ())
        receipt_lines = tuple(
            InventoryReceiptLineCommand(
                purchase_order_line_id=self._require_text(
                    dict(line),
                    "purchaseOrderLineId",
                    "Receipt line data is missing a purchase-order line reference.",
                ),
                quantity_accepted=self._require_non_negative_float(
                    dict(line),
                    "quantityAccepted",
                    "Accepted quantity must be zero or greater.",
                ),
                quantity_rejected=self._require_non_negative_float(
                    dict(line),
                    "quantityRejected",
                    "Rejected quantity must be zero or greater.",
                ),
                unit_cost=self._optional_float(dict(line), "unitCost"),
                notes=self._optional_text(dict(line), "notes") or "",
            )
            for line in raw_lines
        )
        if not receipt_lines:
            raise ValueError(
                "Enter at least one accepted or rejected quantity before posting the receipt."
            )
        if not any(
            line.quantity_accepted > 0 or line.quantity_rejected > 0
            for line in receipt_lines
        ):
            raise ValueError(
                "Enter at least one accepted or rejected quantity before posting the receipt."
            )
        self._desktop_api.post_receipt(
            InventoryReceiptPostCommand(
                purchase_order_id=purchase_order_id,
                receipt_lines=receipt_lines,
                supplier_delivery_reference=self._optional_text(
                    payload,
                    "supplierDeliveryReference",
                )
                or "",
                notes=self._optional_text(payload, "notes") or "",
            )
        )

    @staticmethod
    def _build_overview(
        *,
        all_requisitions,
        filtered_requisitions,
        all_purchase_orders,
        filtered_purchase_orders,
        all_receipts,
    ) -> InventoryCatalogOverviewViewModel:
        awaiting_requisition_count = sum(
            1
            for row in all_requisitions
            if row.status in {"SUBMITTED", "UNDER_REVIEW"}
        )
        awaiting_purchase_order_count = sum(
            1
            for row in all_purchase_orders
            if row.status in {"SUBMITTED", "UNDER_REVIEW"}
        )
        open_receiving_count = sum(
            1
            for row in all_purchase_orders
            if row.status in {"APPROVED", "SENT", "PARTIALLY_RECEIVED"}
        )
        return InventoryCatalogOverviewViewModel(
            title="Procurement",
            subtitle=(
                "Requisitions, supplier commitments, and receipt posting now run "
                "through the module-local procurement desktop API."
            ),
            metrics=(
                InventoryCatalogMetricViewModel(
                    label="Requisitions",
                    value=str(len(all_requisitions)),
                    supporting_text=(
                        f"Showing {len(filtered_requisitions)} requisitions with the current filters."
                    ),
                ),
                InventoryCatalogMetricViewModel(
                    label="Purchase Orders",
                    value=str(len(all_purchase_orders)),
                    supporting_text=(
                        f"Showing {len(filtered_purchase_orders)} purchase orders with the current filters."
                    ),
                ),
                InventoryCatalogMetricViewModel(
                    label="Awaiting Approval",
                    value=str(
                        awaiting_requisition_count + awaiting_purchase_order_count
                    ),
                    supporting_text=(
                        "Combined requisitions and purchase orders still moving through approvals."
                    ),
                ),
                InventoryCatalogMetricViewModel(
                    label="Open Receiving",
                    value=str(open_receiving_count),
                    supporting_text=f"{len(all_receipts)} receipts already posted.",
                ),
            ),
        )

    def _to_requisition_record_view_model(self, row) -> InventoryRecordViewModel:
        return InventoryRecordViewModel(
            id=row.id,
            title=row.requisition_number,
            status_label=row.status_label,
            subtitle=f"{row.requesting_site_label} | {row.requesting_storeroom_label}",
            supporting_text=(
                f"Priority {row.priority or '-'} | Needed {row.needed_by_date_label or '-'}"
            ),
            meta_text=(
                f"Requester {row.requester_username or '-'} | {row.purpose or 'No purpose'}"
            ),
            state={
                "requisitionId": row.id,
                "requestingSiteId": row.requesting_site_id,
                "requestingStoreroomId": row.requesting_storeroom_id,
                "priority": row.priority,
                "status": row.status,
                "version": row.version,
            },
        )

    def _build_requisition_detail(
        self,
        row,
        requisition_lines,
    ) -> InventoryDetailViewModel:
        if row is None:
            return InventoryDetailViewModel(
                title="No requisition selected",
                empty_state=(
                    "Select a requisition to review demand details, add lines, or "
                    "move it into procurement approval."
                ),
            )
        is_draft = row.status == "DRAFT"
        return InventoryDetailViewModel(
            id=row.id,
            title=row.requisition_number,
            status_label=row.status_label,
            subtitle=f"Requester: {row.requester_username or '-'}",
            description=row.purpose or "No purpose recorded.",
            fields=(
                InventoryDetailFieldViewModel(
                    label="Site",
                    value=row.requesting_site_label,
                ),
                InventoryDetailFieldViewModel(
                    label="Storeroom",
                    value=row.requesting_storeroom_label,
                ),
                InventoryDetailFieldViewModel(
                    label="Priority / Needed By",
                    value=f"{row.priority or '-'} / {row.needed_by_date_label or '-'}",
                ),
                InventoryDetailFieldViewModel(
                    label="Source Reference",
                    value=self._format_source_reference(
                        row.source_reference_type,
                        row.source_reference_id,
                    ),
                ),
                InventoryDetailFieldViewModel(
                    label="Workflow Milestones",
                    value=(
                        f"Submitted {row.submitted_at_label or '-'} | "
                        f"Approved {row.approved_at_label or '-'} | "
                        f"Cancelled {row.cancelled_at_label or '-'}"
                    ),
                ),
                InventoryDetailFieldViewModel(
                    label="Notes",
                    value=row.notes or "-",
                ),
            ),
            state={
                "requisitionId": row.id,
                "requestingSiteId": row.requesting_site_id,
                "requestingStoreroomId": row.requesting_storeroom_id,
                "purpose": row.purpose,
                "priority": row.priority,
                "neededByDateIso": row.needed_by_date.isoformat()
                if row.needed_by_date is not None
                else "",
                "notes": row.notes,
                "status": row.status,
                "version": row.version,
                "hasLines": bool(requisition_lines),
                "canEdit": is_draft,
                "canAddLine": is_draft,
                "canSubmit": is_draft and bool(requisition_lines),
                "canCancel": is_draft,
            },
        )

    def _to_requisition_line_record_view_model(self, row) -> InventoryRecordViewModel:
        remaining = max(
            0.0,
            float(row.quantity_requested or 0.0) - float(row.quantity_sourced or 0.0),
        )
        return InventoryRecordViewModel(
            id=row.id,
            title=f"L{row.line_number} - {row.stock_item_label}",
            status_label=row.status_label,
            subtitle=row.description or row.suggested_supplier_label or "-",
            supporting_text=(
                f"Requested {row.quantity_requested_label} | "
                f"Sourced {row.quantity_sourced_label} | "
                f"Remaining {remaining:,.3f}"
            ),
            meta_text=(
                f"Supplier {row.suggested_supplier_label or '-'} | "
                f"Estimated {row.estimated_unit_cost_label}"
            ),
            state={
                "requisitionLineId": row.id,
                "stockItemId": row.stock_item_id,
                "remainingQty": remaining,
            },
        )

    def _to_purchase_order_record_view_model(self, row) -> InventoryRecordViewModel:
        return InventoryRecordViewModel(
            id=row.id,
            title=row.po_number,
            status_label=row.status_label,
            subtitle=f"{row.site_label} | {row.supplier_label}",
            supporting_text=(
                f"Currency {row.currency_code or '-'} | "
                f"Expected {row.expected_delivery_date_label or '-'}"
            ),
            meta_text=(
                f"Source {row.source_requisition_label or '-'} | "
                f"Supplier Ref {row.supplier_reference or '-'}"
            ),
            state={
                "purchaseOrderId": row.id,
                "siteId": row.site_id,
                "supplierPartyId": row.supplier_party_id,
                "currencyCode": row.currency_code,
                "sourceRequisitionId": row.source_requisition_id or "",
                "status": row.status,
                "version": row.version,
            },
        )

    def _build_purchase_order_detail(
        self,
        row,
        purchase_order_lines,
    ) -> InventoryDetailViewModel:
        if row is None:
            return InventoryDetailViewModel(
                title="No purchase order selected",
                empty_state=(
                    "Select a purchase order to review supplier commitments, manage "
                    "lines, or post receipts."
                ),
            )
        is_draft = row.status == "DRAFT"
        outstanding_lines = sum(
            1 for line in purchase_order_lines if self._purchase_order_line_outstanding(line) > 0
        )
        can_receive = row.status in {"APPROVED", "SENT", "PARTIALLY_RECEIVED"} and outstanding_lines > 0
        can_close = row.status in {
            "APPROVED",
            "SENT",
            "PARTIALLY_RECEIVED",
            "FULLY_RECEIVED",
        } and bool(purchase_order_lines) and outstanding_lines == 0
        return InventoryDetailViewModel(
            id=row.id,
            title=row.po_number,
            status_label=row.status_label,
            subtitle=f"Supplier: {row.supplier_label}",
            description=row.notes or "No supplier note recorded.",
            fields=(
                InventoryDetailFieldViewModel(
                    label="Site",
                    value=row.site_label,
                ),
                InventoryDetailFieldViewModel(
                    label="Currency / Supplier Ref",
                    value=f"{row.currency_code or '-'} / {row.supplier_reference or '-'}",
                ),
                InventoryDetailFieldViewModel(
                    label="Order / Expected Delivery",
                    value=f"{row.order_date_label or '-'} / {row.expected_delivery_date_label or '-'}",
                ),
                InventoryDetailFieldViewModel(
                    label="Source Requisition",
                    value=row.source_requisition_label or "-",
                ),
                InventoryDetailFieldViewModel(
                    label="Workflow Milestones",
                    value=(
                        f"Submitted {row.submitted_at_label or '-'} | "
                        f"Approved {row.approved_at_label or '-'} | "
                        f"Sent {row.sent_at_label or '-'} | "
                        f"Cancelled {row.cancelled_at_label or '-'}"
                    ),
                ),
                InventoryDetailFieldViewModel(
                    label="Notes",
                    value=row.notes or "-",
                ),
            ),
            state={
                "purchaseOrderId": row.id,
                "siteId": row.site_id,
                "supplierPartyId": row.supplier_party_id,
                "sourceRequisitionId": row.source_requisition_id or "",
                "currencyCode": row.currency_code,
                "supplierReference": row.supplier_reference,
                "expectedDeliveryDateIso": row.expected_delivery_date.isoformat()
                if row.expected_delivery_date is not None
                else "",
                "notes": row.notes,
                "status": row.status,
                "version": row.version,
                "hasLines": bool(purchase_order_lines),
                "canEdit": is_draft,
                "canAddLine": is_draft,
                "canSubmit": is_draft and bool(purchase_order_lines),
                "canCancel": is_draft,
                "canSend": row.status == "APPROVED",
                "canPostReceipt": can_receive,
                "canClose": can_close,
            },
        )

    def _to_purchase_order_line_record_view_model(self, row) -> InventoryRecordViewModel:
        outstanding = self._purchase_order_line_outstanding(row)
        return InventoryRecordViewModel(
            id=row.id,
            title=f"L{row.line_number} - {row.stock_item_label}",
            status_label=row.status_label,
            subtitle=row.destination_storeroom_label,
            supporting_text=(
                f"Ordered {row.quantity_ordered_label} | "
                f"Received {row.quantity_received_label} | "
                f"Rejected {row.quantity_rejected_label}"
            ),
            meta_text=(
                f"Outstanding {outstanding:,.3f} | Unit price {row.unit_price_label}"
            ),
            state={
                "purchaseOrderLineId": row.id,
                "stockItemId": row.stock_item_id,
                "destinationStoreroomId": row.destination_storeroom_id,
                "outstandingQty": outstanding,
                "uom": row.uom,
                "unitPrice": row.unit_price,
            },
        )

    def _to_receipt_record_view_model(
        self,
        row,
        receipt_lines,
    ) -> InventoryRecordViewModel:
        accepted = sum(float(line.quantity_accepted or 0.0) for line in receipt_lines)
        rejected = sum(float(line.quantity_rejected or 0.0) for line in receipt_lines)
        return InventoryRecordViewModel(
            id=row.id,
            title=row.receipt_number,
            status_label=row.status_label,
            subtitle=f"{row.purchase_order_label} | {row.supplier_label}",
            supporting_text=(
                f"Accepted {accepted:,.3f} | Rejected {rejected:,.3f}"
            ),
            meta_text=(
                f"Posted {row.receipt_date_label or '-'} | "
                f"Delivery ref {row.supplier_delivery_reference or '-'}"
            ),
        )

    def _build_requisition_line_options(
        self,
        requisition_id: str | None,
    ) -> tuple[InventorySelectorOptionViewModel, ...]:
        normalized_id = (requisition_id or "").strip()
        if not normalized_id:
            return ()
        options: list[InventorySelectorOptionViewModel] = []
        for line in self._desktop_api.list_requisition_lines(normalized_id):
            remaining = max(
                0.0,
                float(line.quantity_requested or 0.0)
                - float(line.quantity_sourced or 0.0),
            )
            if remaining <= 0:
                continue
            options.append(
                InventorySelectorOptionViewModel(
                    value=line.id,
                    label=(
                        f"L{line.line_number} | {line.stock_item_label} | "
                        f"Remaining {remaining:,.3f}"
                    ),
                )
            )
        return tuple(options)

    @staticmethod
    def _requisition_matches(
        row,
        search_text: str,
        site_filter: str,
        storeroom_filter: str,
    ) -> bool:
        if site_filter != "all" and row.requesting_site_id != site_filter:
            return False
        if storeroom_filter != "all" and row.requesting_storeroom_id != storeroom_filter:
            return False
        if not search_text:
            return True
        return InventoryProcurementProcurementWorkspacePresenter._matches_search(
            search_text,
            row.requisition_number,
            row.purpose,
            row.priority,
            row.requester_username,
            row.status,
            row.status_label,
            row.requesting_site_label,
            row.requesting_storeroom_label,
        )

    @staticmethod
    def _purchase_order_matches(
        row,
        search_text: str,
        site_filter: str,
        supplier_filter: str,
    ) -> bool:
        if site_filter != "all" and row.site_id != site_filter:
            return False
        if supplier_filter != "all" and row.supplier_party_id != supplier_filter:
            return False
        if not search_text:
            return True
        return InventoryProcurementProcurementWorkspacePresenter._matches_search(
            search_text,
            row.po_number,
            row.supplier_reference,
            row.currency_code,
            row.status,
            row.status_label,
            row.site_label,
            row.supplier_label,
            row.source_requisition_label,
        )

    @staticmethod
    def _purchase_order_line_outstanding(row) -> float:
        return max(
            0.0,
            float(row.quantity_ordered or 0.0)
            - float(row.quantity_received or 0.0)
            - float(row.quantity_rejected or 0.0),
        )

    @staticmethod
    def _build_requisitions_empty_state(
        *,
        all_requisitions,
        filtered_requisitions,
        search_text: str,
        site_filter: str,
        storeroom_filter: str,
        status_filter: str,
    ) -> str:
        if filtered_requisitions:
            return ""
        if not all_requisitions:
            return "No requisitions are available yet. Create a requisition to capture upstream inventory demand."
        if (
            search_text
            or site_filter != "all"
            or storeroom_filter != "all"
            or status_filter != "all"
        ):
            return "No requisitions match the current filters."
        return "No requisitions are available yet."

    @staticmethod
    def _build_purchase_orders_empty_state(
        *,
        all_purchase_orders,
        filtered_purchase_orders,
        search_text: str,
        site_filter: str,
        supplier_filter: str,
        status_filter: str,
    ) -> str:
        if filtered_purchase_orders:
            return ""
        if not all_purchase_orders:
            return "No purchase orders are available yet. Convert approved demand into supplier-facing commitments here."
        if (
            search_text
            or site_filter != "all"
            or supplier_filter != "all"
            or status_filter != "all"
        ):
            return "No purchase orders match the current filters."
        return "No purchase orders are available yet."

    @staticmethod
    def _build_requisition_lines_empty_state(
        *,
        selected_requisition,
        selected_requisition_lines,
    ) -> str:
        if selected_requisition is None:
            return "Select a requisition to review or add demand lines."
        if selected_requisition_lines:
            return ""
        return "This requisition does not have any demand lines yet."

    @staticmethod
    def _build_purchase_order_lines_empty_state(
        *,
        selected_purchase_order,
        selected_purchase_order_lines,
    ) -> str:
        if selected_purchase_order is None:
            return "Select a purchase order to review supplier commitment lines."
        if selected_purchase_order_lines:
            return ""
        return "This purchase order does not have any supplier commitment lines yet."

    @staticmethod
    def _build_receipts_empty_state(
        *,
        selected_purchase_order,
        selected_receipts,
    ) -> str:
        if selected_purchase_order is None:
            return "Select a purchase order to review receipt history or post receiving transactions."
        if selected_receipts:
            return ""
        return "No receipts have been posted for the selected purchase order yet."

    @staticmethod
    def _matches_search(search_text: str, *values: str) -> bool:
        normalized = search_text.casefold()
        return any(normalized in str(value or "").casefold() for value in values)

    @staticmethod
    def _resolve_selected_id(selected_id: str | None, rows) -> str:
        normalized_id = (selected_id or "").strip()
        if normalized_id and any(row.id == normalized_id for row in rows):
            return normalized_id
        if rows:
            return rows[0].id
        return ""

    @staticmethod
    def _normalize_filter(filter_value: str, options) -> str:
        normalized_input = (filter_value or "").strip().casefold()
        for option in options:
            if str(option.value or "").casefold() == normalized_input:
                return option.value
        return options[0].value if options else "all"

    @staticmethod
    def _format_source_reference(source_type: str, source_id: str) -> str:
        left = (source_type or "").strip()
        right = (source_id or "").strip()
        if not left and not right:
            return "-"
        if not right:
            return left
        if not left:
            return right
        return f"{left}: {right}"

    @staticmethod
    def _require_identifier(value: str, message: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError(message)
        return normalized

    @staticmethod
    def _require_text(payload: dict[str, Any], key: str, message: str) -> str:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str) -> str | None:
        value = str(payload.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _optional_float(payload: dict[str, Any], key: str) -> float | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{key} must be a valid number.") from exc

    @staticmethod
    def _optional_int(payload: dict[str, Any], key: str) -> int | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"{key} must be a valid integer.") from exc

    @staticmethod
    def _require_positive_float(payload: dict[str, Any], key: str, message: str) -> float:
        value = InventoryProcurementProcurementWorkspacePresenter._optional_float(
            payload,
            key,
        )
        if value is None or value <= 0:
            raise ValueError(message)
        return value

    @staticmethod
    def _require_non_negative_float(payload: dict[str, Any], key: str, message: str) -> float:
        value = InventoryProcurementProcurementWorkspacePresenter._optional_float(
            payload,
            key,
        )
        if value is None or value < 0:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_date(payload: dict[str, Any], key: str) -> date | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{key} must use YYYY-MM-DD format.") from exc


__all__ = ["InventoryProcurementProcurementWorkspacePresenter"]
