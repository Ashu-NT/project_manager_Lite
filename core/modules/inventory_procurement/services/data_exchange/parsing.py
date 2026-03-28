from __future__ import annotations

from datetime import datetime, timezone

from core.platform.common.exceptions import ValidationError
from core.platform.party import PartyService
from core.modules.inventory_procurement.services.data_exchange.support import (
    optional_text,
    parse_optional_bool,
    parse_optional_date,
    parse_optional_float,
    parse_optional_int,
    text,
)


class InventoryDataExchangeParsingMixin:
    _party_service: PartyService
    
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
        rows,
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
        del requisition_number
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


__all__ = ["InventoryDataExchangeParsingMixin"]
