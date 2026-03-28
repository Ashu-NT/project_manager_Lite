from __future__ import annotations

from datetime import datetime, timezone
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
    optional_text,
    parse_optional_bool,
    parse_optional_date,
    parse_optional_float,
    parse_optional_int,
    stringify_bool,
    text,
    write_rows,
)
from core.modules.inventory_procurement.services.inventory import InventoryService
from core.modules.inventory_procurement.services.item_master import ItemMasterService
from core.modules.inventory_procurement.services.procurement import ProcurementService, PurchasingService
from core.platform.common.exceptions import ValidationError
from core.platform.exporting import (
    ExportArtifactDraft,
    ExportDefinitionRegistry,
    ExportRuntime,
    ensure_output_path,
)
from core.platform.importing import (
    CsvImportRuntime,
    ImportDefinitionRegistry,
    ImportPreview,
    ImportPreviewRow,
    ImportSourceRow,
    ImportSummary,
)
from core.platform.org import SiteService
from core.platform.party import PartyService


class InventoryDataExchangeService:
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

    def _preview_items(self, rows: list[ImportSourceRow]) -> ImportPreview:
        return self._preview_rows(
            rows,
            "items",
            self._item_service.find_item_by_code,
            self._parse_item_payload,
            "item_code",
        )

    def _preview_storerooms(self, rows: list[ImportSourceRow]) -> ImportPreview:
        return self._preview_rows(
            rows,
            "storerooms",
            self._inventory_service.find_storeroom_by_code,
            self._parse_storeroom_payload,
            "storeroom_code",
        )

    def _preview_requisitions(self, rows: list[ImportSourceRow]) -> ImportPreview:
        return self._preview_document_groups(
            rows,
            entity_type="requisitions",
            document_key="requisition_number",
            parser=self._parse_requisition_group,
            existing_finder=self._procurement_service.find_requisition_by_number,
        )

    def _preview_purchase_orders(self, rows: list[ImportSourceRow]) -> ImportPreview:
        return self._preview_document_groups(
            rows,
            entity_type="purchase_orders",
            document_key="po_number",
            parser=self._parse_purchase_order_group,
            existing_finder=self._purchasing_service.find_purchase_order_by_number,
        )

    def _preview_receipts(self, rows: list[ImportSourceRow]) -> ImportPreview:
        return self._preview_document_groups(
            rows,
            entity_type="receipts",
            document_key="receipt_number",
            parser=self._parse_receipt_group,
            existing_finder=self._purchasing_service.find_receipt_by_number,
        )

    def _preview_rows(self, rows, entity_type, finder, parser, code_key):
        preview = ImportPreview(entity_type=entity_type, available_columns=[], mapped_columns={})
        for row in rows:
            code = text(row.values.get(code_key))
            if not code:
                preview.rows.append(self._preview_error_row(row, f"Missing {code_key}."))
                continue
            try:
                existing = finder(code)
                parser(row.values)
            except Exception as exc:
                preview.rows.append(self._preview_error_row(row, str(exc)))
                continue
            preview.rows.append(
                ImportPreviewRow(
                    line_no=row.line_no,
                    status="READY",
                    action="UPDATE" if existing is not None else "CREATE",
                    message=f"Will {'update existing' if existing is not None else 'create'} {entity_type[:-1]}.",
                    row=dict(row.values),
                )
            )
            if existing is not None:
                preview.updated_count += 1
            else:
                preview.created_count += 1
        return preview

    def _preview_document_groups(self, rows, *, entity_type, document_key, parser, existing_finder):
        preview = ImportPreview(entity_type=entity_type, available_columns=[], mapped_columns={})
        for first_line_no, document_number, group_rows in self._group_document_rows(rows, document_key):
            try:
                parser(document_number, group_rows)
                if existing_finder(document_number) is not None:
                    preview.rows.append(
                        ImportPreviewRow(
                            line_no=first_line_no,
                            status="ERROR",
                            action="SKIP",
                            message=f"{entity_type[:-1].replace('_', ' ').title()} number already exists.",
                            row=dict(group_rows[0]),
                        )
                    )
                    continue
            except Exception as exc:
                preview.rows.append(self._preview_error_row(ImportSourceRow(first_line_no, dict(group_rows[0])), str(exc)))
                continue
            preview.rows.append(
                ImportPreviewRow(
                    line_no=first_line_no,
                    status="READY",
                    action="CREATE",
                    message=f"Will create {entity_type[:-1].replace('_', ' ')} with {len(group_rows)} line(s).",
                    row=dict(group_rows[0]),
                )
            )
            preview.created_count += 1
        return preview

    def _import_items(self, rows: list[ImportSourceRow]) -> ImportSummary:
        summary = ImportSummary(entity_type="items")
        for row in rows:
            item_code = text(row.values.get("item_code"))
            if not item_code:
                summary.add_row_error(line_no=row.line_no, field_key="item_code", message="item_code is required.")
                continue
            try:
                payload = self._parse_item_payload(row.values)
                existing = self._item_service.find_item_by_code(item_code)
                if existing is None:
                    self._item_service.create_item(item_code=item_code, **payload)
                    summary.created_count += 1
                else:
                    self._item_service.update_item(existing.id, expected_version=existing.version, **payload)
                    summary.updated_count += 1
            except Exception as exc:
                summary.add_row_error(line_no=row.line_no, message=str(exc))
        return summary

    def _import_storerooms(self, rows: list[ImportSourceRow]) -> ImportSummary:
        summary = ImportSummary(entity_type="storerooms")
        for row in rows:
            storeroom_code = text(row.values.get("storeroom_code"))
            if not storeroom_code:
                summary.add_row_error(
                    line_no=row.line_no,
                    field_key="storeroom_code",
                    message="storeroom_code is required.",
                )
                continue
            try:
                payload = self._parse_storeroom_payload(row.values)
                existing = self._inventory_service.find_storeroom_by_code(storeroom_code)
                if existing is None:
                    self._inventory_service.create_storeroom(storeroom_code=storeroom_code, **payload)
                    summary.created_count += 1
                else:
                    self._inventory_service.update_storeroom(existing.id, expected_version=existing.version, **payload)
                    summary.updated_count += 1
            except Exception as exc:
                summary.add_row_error(line_no=row.line_no, message=str(exc))
        return summary

    def _import_requisitions(self, rows: list[ImportSourceRow]) -> ImportSummary:
        summary = ImportSummary(entity_type="requisitions")
        for first_line_no, document_number, group_rows in self._group_document_rows(rows, "requisition_number"):
            try:
                payload = self._parse_requisition_group(document_number, group_rows)
                if self._procurement_service.find_requisition_by_number(document_number) is not None:
                    raise ValidationError(
                        "Purchase requisition number already exists.",
                        code="INVENTORY_REQUISITION_NUMBER_EXISTS",
                    )
                requisition = self._procurement_service.create_requisition(
                    requesting_site_id=payload["requesting_site_id"],
                    requesting_storeroom_id=payload["requesting_storeroom_id"],
                    purpose=payload["purpose"],
                    needed_by_date=payload["needed_by_date"],
                    priority=payload["priority"],
                    source_reference_type=payload["source_reference_type"],
                    source_reference_id=payload["source_reference_id"],
                    notes=payload["notes"],
                    requisition_number=document_number,
                )
                for line in payload["lines"]:
                    self._procurement_service.add_requisition_line(
                        requisition.id,
                        stock_item_id=line["stock_item_id"],
                        quantity_requested=line["quantity_requested"],
                        uom=line["uom"],
                        description=line["description"],
                        needed_by_date=line["needed_by_date"],
                        estimated_unit_cost=line["estimated_unit_cost"],
                        suggested_supplier_party_id=line["suggested_supplier_party_id"],
                        notes=line["notes"],
                    )
                self._apply_requisition_import_status(requisition.id, payload["status"])
                summary.created_count += 1
            except Exception as exc:
                summary.add_row_error(line_no=first_line_no, message=str(exc))
        return summary

    def _import_purchase_orders(self, rows: list[ImportSourceRow]) -> ImportSummary:
        summary = ImportSummary(entity_type="purchase_orders")
        for first_line_no, document_number, group_rows in self._group_document_rows(rows, "po_number"):
            try:
                payload = self._parse_purchase_order_group(document_number, group_rows)
                if self._purchasing_service.find_purchase_order_by_number(document_number) is not None:
                    raise ValidationError(
                        "Purchase order number already exists.",
                        code="INVENTORY_PURCHASE_ORDER_NUMBER_EXISTS",
                    )
                purchase_order = self._purchasing_service.create_purchase_order(
                    site_id=payload["site_id"],
                    supplier_party_id=payload["supplier_party_id"],
                    currency_code=payload["currency_code"],
                    source_requisition_id=payload["source_requisition_id"],
                    order_date=payload["order_date"],
                    expected_delivery_date=payload["expected_delivery_date"],
                    supplier_reference=payload["supplier_reference"],
                    notes=payload["notes"],
                    po_number=document_number,
                )
                for line in payload["lines"]:
                    self._purchasing_service.add_purchase_order_line(
                        purchase_order.id,
                        stock_item_id=line["stock_item_id"],
                        destination_storeroom_id=line["destination_storeroom_id"],
                        quantity_ordered=line["quantity_ordered"],
                        uom=line["uom"],
                        unit_price=line["unit_price"],
                        expected_delivery_date=line["expected_delivery_date"],
                        description=line["description"],
                        source_requisition_line_id=line["source_requisition_line_id"],
                        notes=line["notes"],
                    )
                self._apply_purchase_order_import_status(purchase_order.id, payload["status"])
                summary.created_count += 1
            except Exception as exc:
                summary.add_row_error(line_no=first_line_no, message=str(exc))
        return summary

    def _import_receipts(self, rows: list[ImportSourceRow]) -> ImportSummary:
        summary = ImportSummary(entity_type="receipts")
        for first_line_no, document_number, group_rows in self._group_document_rows(rows, "receipt_number"):
            try:
                payload = self._parse_receipt_group(document_number, group_rows)
                if self._purchasing_service.find_receipt_by_number(document_number) is not None:
                    raise ValidationError(
                        "Receipt number already exists.",
                        code="INVENTORY_RECEIPT_NUMBER_EXISTS",
                    )
                self._purchasing_service.post_receipt(
                    payload["purchase_order_id"],
                    receipt_lines=payload["lines"],
                    receipt_date=payload["receipt_date"],
                    supplier_delivery_reference=payload["supplier_delivery_reference"],
                    notes=payload["notes"],
                    receipt_number=document_number,
                )
                summary.created_count += 1
            except Exception as exc:
                summary.add_row_error(line_no=first_line_no, message=str(exc))
        return summary

    def _parse_item_payload(self, values: dict[str, str]) -> dict[str, object]:
        name = text(values.get("name"))
        stock_uom = text(values.get("stock_uom"))
        if not name:
            raise ValidationError("name is required.", code="INVENTORY_IMPORT_NAME_REQUIRED")
        if not stock_uom:
            raise ValidationError("stock_uom is required.", code="INVENTORY_IMPORT_STOCK_UOM_REQUIRED")
        payload: dict[str, object] = {"name": name, "stock_uom": stock_uom}
        for key in (
            "description",
            "item_type",
            "status",
            "order_uom",
            "issue_uom",
            "category_code",
            "commodity_code",
            "default_reorder_policy",
            "notes",
        ):
            normalized = optional_text(values.get(key))
            if normalized is not None:
                payload[key] = normalized
        for field_key, label in (
            ("order_uom_ratio", "Order UOM ratio"),
            ("issue_uom_ratio", "Issue UOM ratio"),
            ("min_qty", "Minimum quantity"),
            ("max_qty", "Maximum quantity"),
            ("reorder_point", "Reorder point"),
            ("reorder_qty", "Reorder quantity"),
        ):
            parsed = parse_optional_float(values.get(field_key), label=label)
            if parsed is not None:
                payload[field_key] = parsed
        for field_key, label in (
            ("lead_time_days", "Lead time days"),
            ("shelf_life_days", "Shelf life days"),
        ):
            parsed = parse_optional_int(values.get(field_key), label=label)
            if parsed is not None:
                payload[field_key] = parsed
        for field_key in ("is_stocked", "is_purchase_allowed", "is_lot_tracked", "is_serial_tracked"):
            parsed = parse_optional_bool(values.get(field_key))
            if parsed is not None:
                payload[field_key] = parsed
        preferred_party_code = optional_text(values.get("preferred_party_code"))
        if preferred_party_code is not None:
            payload["preferred_party_id"] = self._resolve_party_id_from_code(
                preferred_party_code,
                label="Preferred party code",
            )
        return payload

    def _parse_storeroom_payload(self, values: dict[str, str]) -> dict[str, object]:
        name = text(values.get("name"))
        site_code = text(values.get("site_code"))
        if not name:
            raise ValidationError("name is required.", code="INVENTORY_IMPORT_NAME_REQUIRED")
        if not site_code:
            raise ValidationError("site_code is required.", code="INVENTORY_IMPORT_SITE_CODE_REQUIRED")
        payload: dict[str, object] = {"name": name, "site_id": self._resolve_site_id_from_code(site_code)}
        for key in ("description", "status", "storeroom_type", "default_currency_code", "notes"):
            normalized = optional_text(values.get(key))
            if normalized is not None:
                payload[key] = normalized
        for field_key in (
            "is_internal_supplier",
            "allows_issue",
            "allows_transfer",
            "allows_receiving",
            "requires_reservation_for_issue",
            "requires_supplier_reference_for_receipt",
        ):
            parsed = parse_optional_bool(values.get(field_key))
            if parsed is not None:
                payload[field_key] = parsed
        manager_party_code = optional_text(values.get("manager_party_code"))
        if manager_party_code is not None:
            payload["manager_party_id"] = self._resolve_party_id_from_code(
                manager_party_code,
                label="Manager party code",
            )
        return payload

    @staticmethod
    def _group_document_rows(
        rows: list[ImportSourceRow],
        document_key: str,
    ) -> list[tuple[int, str, list[dict[str, str]]]]:
        grouped: dict[str, list[tuple[int, dict[str, str]]]] = {}
        order: list[str] = []
        for row in rows:
            document_number = text(row.values.get(document_key))
            if not document_number:
                raise ValidationError(
                    f"{document_key} is required.",
                    code="INVENTORY_IMPORT_DOCUMENT_NUMBER_REQUIRED",
                )
            if document_number not in grouped:
                grouped[document_number] = []
                order.append(document_number)
            grouped[document_number].append((row.line_no, dict(row.values)))
        return [
            (
                grouped[document_number][0][0],
                document_number,
                [values for _line_no, values in grouped[document_number]],
            )
            for document_number in order
        ]

    def _parse_requisition_group(self, requisition_number: str, rows: list[dict[str, str]]) -> dict[str, object]:
        first = rows[0]
        status = (text(first.get("status")).upper() or "DRAFT")
        if status not in {"DRAFT", "SUBMITTED", "APPROVED"}:
            raise ValidationError(
                "Requisition import supports DRAFT, SUBMITTED, and APPROVED status values.",
                code="INVENTORY_IMPORT_STATUS_INVALID",
            )
        payload = {
            "requesting_site_id": self._resolve_site_id_from_code(text(first.get("requesting_site_code"))),
            "requesting_storeroom_id": self._resolve_storeroom_id_from_code(text(first.get("requesting_storeroom_code"))),
            "purpose": text(first.get("purpose")),
            "needed_by_date": parse_optional_date(first.get("needed_by_date"), label="Needed-by date"),
            "priority": text(first.get("priority")) or "NORMAL",
            "source_reference_type": text(first.get("source_reference_type")),
            "source_reference_id": text(first.get("source_reference_id")),
            "status": status,
            "notes": text(first.get("header_notes")),
            "lines": [],
        }
        seen_line_numbers: set[int] = set()
        for row in sorted(rows, key=lambda item: self._parse_line_number(item.get("line_number"))):
            line_number = self._parse_line_number(row.get("line_number"))
            if line_number in seen_line_numbers:
                raise ValidationError(
                    f"Duplicate requisition line number {line_number}.",
                    code="INVENTORY_IMPORT_LINE_NUMBER_DUPLICATE",
                )
            seen_line_numbers.add(line_number)
            payload["lines"].append(
                {
                    "line_number": line_number,
                    "stock_item_id": self._resolve_item_id_from_code(text(row.get("item_code"))),
                    "description": text(row.get("line_description")),
                    "quantity_requested": self._required_float(row.get("quantity_requested"), label="Quantity requested"),
                    "uom": text(row.get("uom")) or None,
                    "needed_by_date": parse_optional_date(row.get("line_needed_by_date"), label="Line needed-by date"),
                    "estimated_unit_cost": parse_optional_float(row.get("estimated_unit_cost"), label="Estimated unit cost") or 0.0,
                    "suggested_supplier_party_id": self._resolve_optional_party_id_from_code(
                        row.get("suggested_supplier_code"),
                        label="Suggested supplier code",
                    ),
                    "notes": text(row.get("line_notes")),
                }
            )
        return payload

    def _parse_purchase_order_group(self, po_number: str, rows: list[dict[str, str]]) -> dict[str, object]:
        del po_number
        first = rows[0]
        status = (text(first.get("status")).upper() or "DRAFT")
        if status not in {"DRAFT", "SUBMITTED", "APPROVED", "SENT"}:
            raise ValidationError(
                "Purchase-order import supports DRAFT, SUBMITTED, APPROVED, and SENT status values.",
                code="INVENTORY_IMPORT_STATUS_INVALID",
            )
        source_requisition_id = None
        source_requisition_number = text(first.get("source_requisition_number"))
        if source_requisition_number:
            requisition = self._procurement_service.find_requisition_by_number(source_requisition_number)
            if requisition is None:
                raise ValidationError(
                    f"Source requisition '{source_requisition_number}' was not found.",
                    code="INVENTORY_IMPORT_REQUISITION_NOT_FOUND",
                )
            source_requisition_id = requisition.id
        payload = {
            "site_id": self._resolve_site_id_from_code(text(first.get("site_code"))),
            "supplier_party_id": self._resolve_party_id_from_code(text(first.get("supplier_code")), label="Supplier code"),
            "currency_code": text(first.get("currency_code")) or None,
            "source_requisition_id": source_requisition_id,
            "order_date": parse_optional_date(first.get("order_date"), label="Order date"),
            "expected_delivery_date": parse_optional_date(first.get("expected_delivery_date"), label="Expected delivery date"),
            "supplier_reference": text(first.get("supplier_reference")),
            "status": status,
            "notes": text(first.get("header_notes")),
            "lines": [],
        }
        seen_line_numbers: set[int] = set()
        for row in sorted(rows, key=lambda item: self._parse_line_number(item.get("line_number"))):
            line_number = self._parse_line_number(row.get("line_number"))
            if line_number in seen_line_numbers:
                raise ValidationError(
                    f"Duplicate purchase-order line number {line_number}.",
                    code="INVENTORY_IMPORT_LINE_NUMBER_DUPLICATE",
                )
            seen_line_numbers.add(line_number)
            payload["lines"].append(
                {
                    "line_number": line_number,
                    "stock_item_id": self._resolve_item_id_from_code(text(row.get("item_code"))),
                    "destination_storeroom_id": self._resolve_storeroom_id_from_code(text(row.get("destination_storeroom_code"))),
                    "description": text(row.get("line_description")),
                    "quantity_ordered": self._required_float(row.get("quantity_ordered"), label="Quantity ordered"),
                    "uom": text(row.get("uom")) or None,
                    "unit_price": parse_optional_float(row.get("unit_price"), label="Unit price") or 0.0,
                    "expected_delivery_date": parse_optional_date(
                        row.get("line_expected_delivery_date"),
                        label="Line expected delivery date",
                    ),
                    "source_requisition_line_id": self._resolve_requisition_line_id_from_ref(
                        row.get("source_requisition_line_ref")
                    ),
                    "notes": text(row.get("line_notes")),
                }
            )
        return payload

    def _parse_receipt_group(self, receipt_number: str, rows: list[dict[str, str]]) -> dict[str, object]:
        del receipt_number
        first = rows[0]
        purchase_order_number = text(first.get("purchase_order_number"))
        purchase_order = self._purchasing_service.find_purchase_order_by_number(purchase_order_number)
        if purchase_order is None:
            raise ValidationError(
                f"Purchase order '{purchase_order_number}' was not found.",
                code="INVENTORY_IMPORT_PURCHASE_ORDER_NOT_FOUND",
            )
        line_lookup = {
            line.line_number: line.id
            for line in self._purchasing_service.list_purchase_order_lines(purchase_order.id)
        }
        receipt_date = parse_optional_date(first.get("receipt_date"), label="Receipt date")
        payload = {
            "purchase_order_id": purchase_order.id,
            "receipt_date": (
                datetime.combine(receipt_date, datetime.min.time(), tzinfo=timezone.utc)
                if receipt_date is not None
                else None
            ),
            "supplier_delivery_reference": text(first.get("supplier_delivery_reference")),
            "notes": text(first.get("header_notes")),
            "lines": [],
        }
        seen_line_numbers: set[int] = set()
        for row in sorted(rows, key=lambda item: self._parse_line_number(item.get("line_number"))):
            line_number = self._parse_line_number(row.get("line_number"))
            if line_number in seen_line_numbers:
                raise ValidationError(
                    f"Duplicate receipt line number {line_number}.",
                    code="INVENTORY_IMPORT_LINE_NUMBER_DUPLICATE",
                )
            seen_line_numbers.add(line_number)
            purchase_order_line_number = self._parse_line_number(row.get("purchase_order_line_number"))
            purchase_order_line_id = line_lookup.get(purchase_order_line_number)
            if purchase_order_line_id is None:
                raise ValidationError(
                    f"Purchase-order line {purchase_order_line_number} was not found on the selected order.",
                    code="INVENTORY_IMPORT_PURCHASE_ORDER_LINE_NOT_FOUND",
                )
            payload["lines"].append(
                {
                    "purchase_order_line_id": purchase_order_line_id,
                    "quantity_accepted": self._required_float(row.get("quantity_accepted"), label="Quantity accepted"),
                    "quantity_rejected": parse_optional_float(row.get("quantity_rejected"), label="Quantity rejected") or 0.0,
                    "unit_cost": parse_optional_float(row.get("unit_cost"), label="Unit cost"),
                    "lot_number": text(row.get("lot_number")),
                    "serial_number": text(row.get("serial_number")),
                    "expiry_date": parse_optional_date(row.get("expiry_date"), label="Expiry date"),
                    "notes": text(row.get("line_notes")),
                }
            )
        return payload

    @staticmethod
    def _parse_line_number(value: object) -> int:
        parsed = parse_optional_int(str(value or ""), label="Line number")
        if parsed is None or parsed <= 0:
            raise ValidationError("Line number is required.", code="INVENTORY_IMPORT_LINE_NUMBER_REQUIRED")
        return parsed

    @staticmethod
    def _required_float(value: object, *, label: str) -> float:
        parsed = parse_optional_float(str(value or ""), label=label)
        if parsed is None:
            raise ValidationError(f"{label} is required.", code="INVENTORY_IMPORT_NUMBER_REQUIRED")
        return parsed

    def _resolve_item_id_from_code(self, item_code: str) -> str:
        item = self._item_service.find_item_by_code(item_code)
        if item is None:
            raise ValidationError(
                f"Item code '{item_code}' was not found in the active organization.",
                code="INVENTORY_IMPORT_ITEM_NOT_FOUND",
            )
        return item.id

    def _resolve_storeroom_id_from_code(self, storeroom_code: str) -> str:
        storeroom = self._inventory_service.find_storeroom_by_code(storeroom_code)
        if storeroom is None:
            raise ValidationError(
                f"Storeroom code '{storeroom_code}' was not found in the active organization.",
                code="INVENTORY_IMPORT_STOREROOM_NOT_FOUND",
            )
        return storeroom.id

    def _resolve_optional_party_id_from_code(self, party_code: str | None, *, label: str) -> str | None:
        normalized_code = optional_text(party_code)
        if normalized_code is None:
            return None
        return self._resolve_party_id_from_code(normalized_code, label=label)

    def _resolve_requisition_line_id_from_ref(self, value: str | None) -> str | None:
        normalized = optional_text(value)
        if normalized is None:
            return None
        requisition_number, separator, line_number_text = normalized.partition(":")
        if not separator:
            raise ValidationError(
                "Source requisition line ref must use REQUISITION_NUMBER:LINE_NUMBER format.",
                code="INVENTORY_IMPORT_REQUISITION_LINE_REF_INVALID",
            )
        requisition = self._procurement_service.find_requisition_by_number(requisition_number)
        if requisition is None:
            raise ValidationError(
                f"Source requisition '{requisition_number}' was not found.",
                code="INVENTORY_IMPORT_REQUISITION_NOT_FOUND",
            )
        line_number = self._parse_line_number(line_number_text)
        for line in self._procurement_service.list_requisition_lines(requisition.id):
            if int(line.line_number) == line_number:
                return line.id
        raise ValidationError(
            f"Source requisition line '{normalized}' was not found.",
            code="INVENTORY_IMPORT_REQUISITION_LINE_NOT_FOUND",
        )

    def _apply_requisition_import_status(self, requisition_id: str, status: str) -> None:
        normalized_status = str(status or "DRAFT").strip().upper() or "DRAFT"
        if normalized_status == "DRAFT":
            return
        requisition = self._procurement_service.submit_requisition(
            requisition_id,
            note="Submitted from inventory requisition import.",
        )
        if normalized_status == "SUBMITTED":
            return
        if self._approval_service is None:
            raise ValidationError(
                "Approval service is required to import approved requisitions.",
                code="INVENTORY_IMPORT_APPROVAL_SERVICE_REQUIRED",
            )
        self._approval_service.approve_and_apply(
            requisition.approval_request_id,
            note="Approved from inventory requisition import.",
        )

    def _apply_purchase_order_import_status(self, purchase_order_id: str, status: str) -> None:
        normalized_status = str(status or "DRAFT").strip().upper() or "DRAFT"
        if normalized_status == "DRAFT":
            return
        purchase_order = self._purchasing_service.submit_purchase_order(
            purchase_order_id,
            note="Submitted from inventory purchase-order import.",
        )
        if normalized_status == "SUBMITTED":
            return
        if self._approval_service is None:
            raise ValidationError(
                "Approval service is required to import approved purchase orders.",
                code="INVENTORY_IMPORT_APPROVAL_SERVICE_REQUIRED",
            )
        self._approval_service.approve_and_apply(
            purchase_order.approval_request_id,
            note="Approved from inventory purchase-order import.",
        )
        if normalized_status == "SENT":
            self._purchasing_service.send_purchase_order(
                purchase_order_id,
                note="Sent from inventory purchase-order import.",
            )

    def _resolve_site_id_from_code(self, site_code: str) -> str:
        site = self._site_service.find_site_by_code(site_code)
        if site is None:
            raise ValidationError(
                f"Site code '{site_code}' was not found in the active organization.",
                code="INVENTORY_IMPORT_SITE_NOT_FOUND",
            )
        return site.id

    def _resolve_party_id_from_code(self, party_code: str, *, label: str) -> str:
        party = self._party_service.find_party_by_code(party_code)
        if party is None:
            raise ValidationError(
                f"{label} '{party_code}' was not found in the active organization.",
                code="INVENTORY_IMPORT_PARTY_NOT_FOUND",
            )
        return party.id

    @staticmethod
    def _preview_error_row(row: ImportSourceRow, message: str) -> ImportPreviewRow:
        return ImportPreviewRow(
            line_no=row.line_no,
            status="ERROR",
            action="SKIP",
            message=message,
            row=dict(row.values),
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
