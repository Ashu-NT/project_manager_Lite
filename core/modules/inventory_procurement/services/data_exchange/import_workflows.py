from __future__ import annotations

from core.platform.common.exceptions import ValidationError
from core.platform.importing import (
    ImportPreview,
    ImportPreviewRow,
    ImportSourceRow,
    ImportSummary,
)

from core.modules.inventory_procurement.services.data_exchange.support import text


class InventoryDataExchangeImportMixin:
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
                preview.rows.append(
                    self._preview_error_row(ImportSourceRow(first_line_no, dict(group_rows[0])), str(exc))
                )
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

    @staticmethod
    def _preview_error_row(row: ImportSourceRow, message: str) -> ImportPreviewRow:
        return ImportPreviewRow(
            line_no=row.line_no,
            status="ERROR",
            action="SKIP",
            message=message,
            row=dict(row.values),
        )


__all__ = ["InventoryDataExchangeImportMixin"]
