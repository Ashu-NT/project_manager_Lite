from __future__ import annotations

from pathlib import Path

from core.modules.inventory_procurement.exporting import (
    register_inventory_procurement_export_definitions,
)
from core.modules.inventory_procurement.importing import (
    register_inventory_procurement_import_definitions,
)
from core.modules.inventory_procurement.interfaces import (
    PurchaseOrderLineRepository,
    PurchaseRequisitionLineRepository,
    ReceiptLineRepository,
)
from core.modules.inventory_procurement.services.data_exchange.import_workflows import (
    InventoryDataExchangeImportMixin,
)
from core.modules.inventory_procurement.services.data_exchange.parsing import (
    InventoryDataExchangeParsingMixin,
)
from core.modules.inventory_procurement.services.data_exchange.support import (
    ITEM_EXPORT_FIELDS,
    ITEM_FIELDS,
    PURCHASE_ORDER_FIELDS,
    PURCHASE_ORDER_EXPORT_FIELDS,
    RECEIPT_FIELDS,
    RECEIPT_EXPORT_FIELDS,
    REQUISITION_FIELDS,
    REQUISITION_EXPORT_FIELDS,
    STOREROOM_EXPORT_FIELDS,
    STOREROOM_FIELDS,
    InventoryExportRequest,
    enum_value,
    isoformat,
    stringify_bool,
    write_rows,
)
from core.modules.inventory_procurement.services.inventory import InventoryService
from core.modules.inventory_procurement.services.item_master import ItemMasterService
from core.modules.inventory_procurement.services.procurement import ProcurementService, PurchasingService
from src.core.platform.exporting import (
    ExportArtifactDraft,
    ExportDefinitionRegistry,
    ExportRuntime,
    ensure_output_path,
)
from src.core.platform.importing import (
    CsvImportRuntime,
    ImportDefinitionRegistry,
    ImportPreview,
    ImportSummary,
)
from src.core.platform.org import SiteService
from src.core.platform.party import PartyService


class InventoryDataExchangeService(
    InventoryDataExchangeImportMixin,
    InventoryDataExchangeParsingMixin,
):
    _IMPORT_SCHEMAS = {
        "items": ITEM_FIELDS,
        "storerooms": STOREROOM_FIELDS,
        "requisitions": REQUISITION_FIELDS,
        "purchase_orders": PURCHASE_ORDER_FIELDS,
        "receipts": RECEIPT_FIELDS,
    }

    def __init__(
        self,
        *,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        procurement_service: ProcurementService,
        purchasing_service: PurchasingService,
        approval_service=None,
        site_service: SiteService,
        party_service: PartyService,
        requisition_line_repo: PurchaseRequisitionLineRepository,
        purchase_order_line_repo: PurchaseOrderLineRepository,
        receipt_line_repo: ReceiptLineRepository,
        user_session=None,
        module_catalog_service=None,
        runtime_execution_service=None,
        import_registry: ImportDefinitionRegistry | None = None,
        export_registry: ExportDefinitionRegistry | None = None,
        import_runtime: CsvImportRuntime | None = None,
        export_runtime: ExportRuntime | None = None,
    ) -> None:
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._procurement_service = procurement_service
        self._purchasing_service = purchasing_service
        self._approval_service = approval_service
        self._site_service = site_service
        self._party_service = party_service
        self._requisition_line_repo = requisition_line_repo
        self._purchase_order_line_repo = purchase_order_line_repo
        self._receipt_line_repo = receipt_line_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

        registry = import_registry or ImportDefinitionRegistry()
        register_inventory_procurement_import_definitions(
            registry,
            schemas=self._IMPORT_SCHEMAS,
            preview_handlers={
                "items": self._preview_items,
                "storerooms": self._preview_storerooms,
                "requisitions": self._preview_requisitions,
                "purchase_orders": self._preview_purchase_orders,
                "receipts": self._preview_receipts,
            },
            execution_handlers={
                "items": self._import_items,
                "storerooms": self._import_storerooms,
                "requisitions": self._import_requisitions,
                "purchase_orders": self._import_purchase_orders,
                "receipts": self._import_receipts,
            },
        )
        self._import_runtime = import_runtime or CsvImportRuntime(
            registry,
            user_session=user_session,
            module_catalog_service=module_catalog_service,
            runtime_execution_service=runtime_execution_service,
        )

        export_registry_instance = export_registry or ExportDefinitionRegistry()
        register_inventory_procurement_export_definitions(
            export_registry_instance,
            export_handlers={
                "items": self._export_items,
                "storerooms": self._export_storerooms,
                "requisitions": self._export_requisitions,
                "purchase_orders": self._export_purchase_orders,
                "receipts": self._export_receipts,
            },
        )
        self._export_runtime = export_runtime or ExportRuntime(
            export_registry_instance,
            user_session=user_session,
            module_catalog_service=module_catalog_service,
            runtime_execution_service=runtime_execution_service,
        )

    def get_import_schema(self, entity_type: str):
        return self._import_runtime.get_import_schema(
            entity_type,
            user_session=self._user_session,
            module_catalog_service=self._module_catalog_service,
        )

    def read_csv_columns(self, file_path: str | Path) -> list[str]:
        return self._import_runtime.read_csv_columns(file_path)

    def preview_csv(
        self,
        entity_type: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
        max_rows: int = 100,
    ) -> ImportPreview:
        return self._import_runtime.preview_csv(
            entity_type,
            file_path,
            column_mapping=column_mapping,
            max_rows=max_rows,
            user_session=self._user_session,
            module_catalog_service=self._module_catalog_service,
        )

    def import_csv(
        self,
        entity_type: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
    ) -> ImportSummary:
        return self._import_runtime.import_csv(
            entity_type,
            file_path,
            column_mapping=column_mapping,
            user_session=self._user_session,
            module_catalog_service=self._module_catalog_service,
        )

    def export_csv(
        self,
        entity_type: str,
        output_path: str | Path,
        *,
        active_only: bool | None = None,
        status: str | None = None,
        site_id: str | None = None,
        storeroom_id: str | None = None,
        supplier_party_id: str | None = None,
        purchase_order_id: str | None = None,
        limit: int = 200,
    ):
        return self._export_runtime.export(
            entity_type,
            InventoryExportRequest(
                output_path=Path(output_path),
                active_only=active_only,
                status=status,
                site_id=site_id,
                storeroom_id=storeroom_id,
                supplier_party_id=supplier_party_id,
                purchase_order_id=purchase_order_id,
                limit=limit,
            ),
            user_session=self._user_session,
            module_catalog_service=self._module_catalog_service,
        )

    def _export_items(self, request: object) -> ExportArtifactDraft:
        assert isinstance(request, InventoryExportRequest)
        rows = self._item_service.list_items(active_only=request.active_only)
        output_path = ensure_output_path(request.output_path)
        party_codes = self._party_codes_by_id()
        write_rows(
            output_path,
            ITEM_EXPORT_FIELDS,
            [
                {
                    "item_code": item.item_code,
                    "name": item.name,
                    "description": item.description,
                    "item_type": item.item_type,
                    "status": enum_value(item.status),
                    "stock_uom": item.stock_uom,
                    "order_uom": item.order_uom,
                    "issue_uom": item.issue_uom,
                    "order_uom_ratio": item.order_uom_ratio,
                    "issue_uom_ratio": item.issue_uom_ratio,
                    "category_code": item.category_code,
                    "commodity_code": item.commodity_code,
                    "is_stocked": stringify_bool(item.is_stocked),
                    "is_purchase_allowed": stringify_bool(item.is_purchase_allowed),
                    "default_reorder_policy": item.default_reorder_policy,
                    "min_qty": item.min_qty,
                    "max_qty": item.max_qty,
                    "reorder_point": item.reorder_point,
                    "reorder_qty": item.reorder_qty,
                    "lead_time_days": item.lead_time_days if item.lead_time_days is not None else "",
                    "is_lot_tracked": stringify_bool(item.is_lot_tracked),
                    "is_serial_tracked": stringify_bool(item.is_serial_tracked),
                    "shelf_life_days": item.shelf_life_days if item.shelf_life_days is not None else "",
                    "preferred_party_code": party_codes.get(item.preferred_party_id or "", ""),
                    "notes": item.notes,
                }
                for item in rows
            ],
        )
        return ExportArtifactDraft(output_path, media_type="text/csv")

    def _export_storerooms(self, request: object) -> ExportArtifactDraft:
        assert isinstance(request, InventoryExportRequest)
        rows = self._inventory_service.list_storerooms(active_only=request.active_only, site_id=request.site_id)
        output_path = ensure_output_path(request.output_path)
        site_codes = self._site_codes_by_id()
        party_codes = self._party_codes_by_id()
        write_rows(
            output_path,
            STOREROOM_EXPORT_FIELDS,
            [
                {
                    "storeroom_code": storeroom.storeroom_code,
                    "name": storeroom.name,
                    "site_code": site_codes.get(storeroom.site_id, ""),
                    "description": storeroom.description,
                    "status": enum_value(storeroom.status),
                    "storeroom_type": storeroom.storeroom_type,
                    "is_internal_supplier": stringify_bool(storeroom.is_internal_supplier),
                    "allows_issue": stringify_bool(storeroom.allows_issue),
                    "allows_transfer": stringify_bool(storeroom.allows_transfer),
                    "allows_receiving": stringify_bool(storeroom.allows_receiving),
                    "requires_reservation_for_issue": stringify_bool(storeroom.requires_reservation_for_issue),
                    "requires_supplier_reference_for_receipt": stringify_bool(
                        storeroom.requires_supplier_reference_for_receipt
                    ),
                    "default_currency_code": storeroom.default_currency_code,
                    "manager_party_code": party_codes.get(storeroom.manager_party_id or "", ""),
                    "notes": storeroom.notes,
                }
                for storeroom in rows
            ],
        )
        return ExportArtifactDraft(output_path, media_type="text/csv")

    def _item_codes_by_id(self) -> dict[str, str]:
        return {item.id: item.item_code for item in self._item_service.list_items(active_only=None)}

    def _storeroom_codes_by_id(self) -> dict[str, str]:
        return {
            storeroom.id: storeroom.storeroom_code
            for storeroom in self._inventory_service.list_storerooms(active_only=None)
        }

    def _site_codes_by_id(self) -> dict[str, str]:
        return {site.id: site.site_code for site in self._site_service.list_sites(active_only=None)}

    def _party_codes_by_id(self) -> dict[str, str]:
        return {party.id: party.party_code for party in self._party_service.list_parties(active_only=None)}

    def _export_requisitions(self, request: object) -> ExportArtifactDraft:
        assert isinstance(request, InventoryExportRequest)
        requisitions = self._procurement_service.list_requisitions(
            status=request.status,
            site_id=request.site_id,
            storeroom_id=request.storeroom_id,
            limit=request.limit,
        )
        output_path = ensure_output_path(request.output_path)
        item_codes = self._item_codes_by_id()
        storeroom_codes = self._storeroom_codes_by_id()
        site_codes = self._site_codes_by_id()
        party_codes = self._party_codes_by_id()
        rows: list[dict[str, object]] = []
        for requisition in requisitions:
            for line in self._procurement_service.list_requisition_lines(requisition.id) or [None]:
                rows.append(
                    {
                        "requisition_number": requisition.requisition_number,
                        "status": enum_value(requisition.status),
                        "requesting_site_code": site_codes.get(requisition.requesting_site_id, ""),
                        "requesting_storeroom_code": storeroom_codes.get(requisition.requesting_storeroom_id, ""),
                        "requester_username": requisition.requester_username,
                        "needed_by_date": isoformat(requisition.needed_by_date),
                        "priority": requisition.priority,
                        "approval_request_id": requisition.approval_request_id or "",
                        "source_reference_type": requisition.source_reference_type,
                        "source_reference_id": requisition.source_reference_id,
                        "submitted_at": isoformat(requisition.submitted_at),
                        "approved_at": isoformat(requisition.approved_at),
                        "cancelled_at": isoformat(requisition.cancelled_at),
                        "purpose": requisition.purpose,
                        "line_number": "" if line is None else line.line_number,
                        "item_code": "" if line is None else item_codes.get(line.stock_item_id, ""),
                        "line_description": "" if line is None else line.description,
                        "quantity_requested": "" if line is None else line.quantity_requested,
                        "uom": "" if line is None else line.uom,
                        "line_needed_by_date": "" if line is None else isoformat(line.needed_by_date),
                        "estimated_unit_cost": "" if line is None else line.estimated_unit_cost,
                        "quantity_sourced": "" if line is None else line.quantity_sourced,
                        "suggested_supplier_code": "" if line is None else party_codes.get(line.suggested_supplier_party_id or "", ""),
                        "line_status": "" if line is None else enum_value(line.status),
                        "line_notes": "" if line is None else line.notes,
                        "header_notes": requisition.notes,
                    }
                )
        write_rows(output_path, REQUISITION_EXPORT_FIELDS, rows)
        return ExportArtifactDraft(output_path, media_type="text/csv")

    def _export_purchase_orders(self, request: object) -> ExportArtifactDraft:
        assert isinstance(request, InventoryExportRequest)
        purchase_orders = self._purchasing_service.list_purchase_orders(
            status=request.status,
            site_id=request.site_id,
            supplier_party_id=request.supplier_party_id,
            limit=request.limit,
        )
        output_path = ensure_output_path(request.output_path)
        item_codes = self._item_codes_by_id()
        storeroom_codes = self._storeroom_codes_by_id()
        site_codes = self._site_codes_by_id()
        party_codes = self._party_codes_by_id()
        requisition_lookup = self._requisition_lookup_by_id()
        requisition_line_lookup = self._requisition_line_ref_by_id()
        rows: list[dict[str, object]] = []
        for purchase_order in purchase_orders:
            for line in self._purchasing_service.list_purchase_order_lines(purchase_order.id) or [None]:
                rows.append(
                    {
                        "po_number": purchase_order.po_number,
                        "status": enum_value(purchase_order.status),
                        "site_code": site_codes.get(purchase_order.site_id, ""),
                        "supplier_code": party_codes.get(purchase_order.supplier_party_id, ""),
                        "order_date": isoformat(purchase_order.order_date),
                        "expected_delivery_date": isoformat(purchase_order.expected_delivery_date),
                        "currency_code": purchase_order.currency_code,
                        "approval_request_id": purchase_order.approval_request_id or "",
                        "source_requisition_number": requisition_lookup.get(purchase_order.source_requisition_id or "", ""),
                        "supplier_reference": purchase_order.supplier_reference,
                        "submitted_at": isoformat(purchase_order.submitted_at),
                        "approved_at": isoformat(purchase_order.approved_at),
                        "sent_at": isoformat(purchase_order.sent_at),
                        "closed_at": isoformat(purchase_order.closed_at),
                        "cancelled_at": isoformat(purchase_order.cancelled_at),
                        "line_number": "" if line is None else line.line_number,
                        "item_code": "" if line is None else item_codes.get(line.stock_item_id, ""),
                        "destination_storeroom_code": "" if line is None else storeroom_codes.get(line.destination_storeroom_id, ""),
                        "line_description": "" if line is None else line.description,
                        "quantity_ordered": "" if line is None else line.quantity_ordered,
                        "quantity_received": "" if line is None else line.quantity_received,
                        "quantity_rejected": "" if line is None else line.quantity_rejected,
                        "uom": "" if line is None else line.uom,
                        "unit_price": "" if line is None else line.unit_price,
                        "line_expected_delivery_date": "" if line is None else isoformat(line.expected_delivery_date),
                        "source_requisition_line_ref": "" if line is None else requisition_line_lookup.get(line.source_requisition_line_id or "", ""),
                        "line_status": "" if line is None else enum_value(line.status),
                        "line_notes": "" if line is None else line.notes,
                        "header_notes": purchase_order.notes,
                    }
                )
        write_rows(output_path, PURCHASE_ORDER_EXPORT_FIELDS, rows)
        return ExportArtifactDraft(output_path, media_type="text/csv")

    def _export_receipts(self, request: object) -> ExportArtifactDraft:
        assert isinstance(request, InventoryExportRequest)
        receipts = self._purchasing_service.list_receipts(purchase_order_id=request.purchase_order_id, limit=request.limit)
        output_path = ensure_output_path(request.output_path)
        purchase_order_lookup = {
            purchase_order.id: purchase_order.po_number
            for purchase_order in self._purchasing_service.list_purchase_orders(limit=max(request.limit, 500))
        }
        purchase_order_line_lookup = self._purchase_order_line_number_by_id()
        item_codes = self._item_codes_by_id()
        storeroom_codes = self._storeroom_codes_by_id()
        site_codes = self._site_codes_by_id()
        party_codes = self._party_codes_by_id()
        rows: list[dict[str, object]] = []
        for receipt in receipts:
            for line in self._purchasing_service.list_receipt_lines(receipt.id) or [None]:
                rows.append(
                    {
                        "receipt_number": receipt.receipt_number,
                        "purchase_order_number": purchase_order_lookup.get(receipt.purchase_order_id, ""),
                        "received_site_code": site_codes.get(receipt.received_site_id, ""),
                        "supplier_code": party_codes.get(receipt.supplier_party_id, ""),
                        "status": enum_value(receipt.status),
                        "receipt_date": isoformat(receipt.receipt_date),
                        "supplier_delivery_reference": receipt.supplier_delivery_reference,
                        "received_by_username": receipt.received_by_username,
                        "line_number": "" if line is None else line.line_number,
                        "purchase_order_line_number": "" if line is None else purchase_order_line_lookup.get(line.purchase_order_line_id, ""),
                        "item_code": "" if line is None else item_codes.get(line.stock_item_id, ""),
                        "storeroom_code": "" if line is None else storeroom_codes.get(line.storeroom_id, ""),
                        "quantity_accepted": "" if line is None else line.quantity_accepted,
                        "quantity_rejected": "" if line is None else line.quantity_rejected,
                        "uom": "" if line is None else line.uom,
                        "unit_cost": "" if line is None else line.unit_cost,
                        "lot_number": "" if line is None else line.lot_number,
                        "serial_number": "" if line is None else line.serial_number,
                        "expiry_date": "" if line is None else isoformat(line.expiry_date),
                        "line_notes": "" if line is None else line.notes,
                        "header_notes": receipt.notes,
                    }
                )
        write_rows(output_path, RECEIPT_EXPORT_FIELDS, rows)
        return ExportArtifactDraft(output_path, media_type="text/csv")

    def _requisition_lookup_by_id(self) -> dict[str, str]:
        return {
            requisition.id: requisition.requisition_number
            for requisition in self._procurement_service.list_requisitions(limit=500)
        }

    def _requisition_line_ref_by_id(self) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for requisition in self._procurement_service.list_requisitions(limit=500):
            for line in self._requisition_line_repo.list_for_requisition(requisition.id):
                lookup[line.id] = f"{requisition.requisition_number}:{line.line_number}"
        return lookup

    def _purchase_order_line_number_by_id(self) -> dict[str, int]:
        lookup: dict[str, int] = {}
        for purchase_order in self._purchasing_service.list_purchase_orders(limit=500):
            for line in self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id):
                lookup[line.id] = line.line_number
        return lookup


__all__ = ["InventoryDataExchangeService"]
