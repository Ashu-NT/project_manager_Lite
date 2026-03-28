from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from core.modules.inventory_procurement.domain import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderLineStatus,
    PurchaseOrderStatus,
    PurchaseRequisition,
    PurchaseRequisitionLine,
    PurchaseRequisitionLineStatus,
    PurchaseRequisitionStatus,
    StockBalance,
    StockItem,
)
from core.modules.inventory_procurement.support import (
    REQUISITION_STATUS_TRANSITIONS,
    convert_item_quantity,
    normalize_optional_text,
    normalize_positive_quantity,
    validate_transition,
)
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ValidationError
from core.platform.org.domain import Organization


def build_purchase_order_number() -> str:
    return f"INV-PO-{uuid4().hex[:10].upper()}"


def build_receipt_number() -> str:
    return f"INV-RCV-{uuid4().hex[:10].upper()}"


def normalize_currency_code(value: str | None, *, fallback: str = "") -> str:
    normalized = normalize_optional_text(value).upper() or normalize_optional_text(fallback).upper()
    if not normalized:
        raise ValidationError("Currency code is required.", code="INVENTORY_CURRENCY_REQUIRED")
    return normalized


class PurchasingSupportMixin:
    def _validate_source_requisition(
        self,
        source_requisition_id: str | None,
        organization_id: str,
    ) -> PurchaseRequisition | None:
        requisition_id = normalize_optional_text(source_requisition_id)
        if not requisition_id:
            return None
        requisition = self._requisition_repo.get(requisition_id)
        if requisition is None or requisition.organization_id != organization_id:
            raise ValidationError("Source requisition was not found in the active organization.", code="INVENTORY_REQUISITION_SCOPE_INVALID")
        if requisition.status not in {PurchaseRequisitionStatus.APPROVED, PurchaseRequisitionStatus.PARTIALLY_SOURCED}:
            raise ValidationError("Source requisition is not ready for purchasing.", code="INVENTORY_REQUISITION_STATUS_INVALID")
        return requisition

    def _validate_source_requisition_line(
        self,
        *,
        purchase_order: PurchaseOrder,
        item: StockItem,
        source_requisition_line_id: str | None,
        quantity_ordered: float,
        quantity_ordered_uom: str,
    ) -> PurchaseRequisitionLine | None:
        line_id = normalize_optional_text(source_requisition_line_id)
        if not line_id:
            return None
        requisition_line = self._require_requisition_line(line_id)
        if requisition_line.stock_item_id != item.id:
            raise ValidationError(
                "Source requisition line must reference the same stock item.",
                code="INVENTORY_REQUISITION_LINE_SCOPE_INVALID",
            )
        if purchase_order.source_requisition_id and requisition_line.purchase_requisition_id != purchase_order.source_requisition_id:
            raise ValidationError("Source requisition line does not belong to the purchase-order requisition.", code="INVENTORY_REQUISITION_LINE_SCOPE_INVALID")
        remaining = max(0.0, float(requisition_line.quantity_requested or 0.0) - float(requisition_line.quantity_sourced or 0.0))
        if remaining <= 0:
            raise ValidationError("Source requisition line is already fully sourced.", code="INVENTORY_REQUISITION_LINE_FULLY_SOURCED")
        ordered_in_requisition_uom = convert_item_quantity(
            item,
            normalize_positive_quantity(quantity_ordered, label="Purchase-order quantity"),
            from_uom=quantity_ordered_uom,
            to_uom=requisition_line.uom,
            label="Purchase-order line UOM",
        )
        if ordered_in_requisition_uom > remaining:
            raise ValidationError("Purchase-order quantity exceeds the remaining requisition demand.", code="INVENTORY_REQUISITION_LINE_QTY_EXCEEDED")
        return requisition_line

    def _require_draft_purchase_order(self, purchase_order_id: str) -> PurchaseOrder:
        purchase_order = self.get_purchase_order(purchase_order_id)
        if purchase_order.status != PurchaseOrderStatus.DRAFT:
            raise ValidationError("Only draft purchase orders can be edited.", code="INVENTORY_PURCHASE_ORDER_NOT_DRAFT")
        return purchase_order

    def _require_requisition_line(self, line_id: str) -> PurchaseRequisitionLine:
        line = self._requisition_line_repo.get(line_id)
        if line is None:
            raise ValidationError("Source requisition line not found.", code="INVENTORY_REQUISITION_LINE_NOT_FOUND")
        return line

    def _line_outstanding_qty(self, line: PurchaseOrderLine) -> float:
        return max(0.0, float(line.quantity_ordered or 0.0) - float(line.quantity_received or 0.0) - float(line.quantity_rejected or 0.0))

    def _is_purchase_order_fully_processed(self, lines: list[PurchaseOrderLine]) -> bool:
        return bool(lines) and all(self._line_outstanding_qty(line) <= 0 for line in lines)

    def _resolve_purchase_order_line_status(
        self,
        line: PurchaseOrderLine,
        *,
        treat_open: bool = False,
    ) -> PurchaseOrderLineStatus:
        processed = float(line.quantity_received or 0.0) + float(line.quantity_rejected or 0.0)
        ordered = float(line.quantity_ordered or 0.0)
        if processed <= 0:
            return PurchaseOrderLineStatus.OPEN if treat_open else PurchaseOrderLineStatus.DRAFT
        if processed >= ordered:
            return PurchaseOrderLineStatus.FULLY_RECEIVED
        return PurchaseOrderLineStatus.PARTIALLY_RECEIVED

    def _resolve_purchase_order_receiving_status(self, lines: list[PurchaseOrderLine]) -> PurchaseOrderStatus:
        if self._is_purchase_order_fully_processed(lines):
            return PurchaseOrderStatus.FULLY_RECEIVED
        return PurchaseOrderStatus.PARTIALLY_RECEIVED

    def _resolve_requisition_line_status(self, line: PurchaseRequisitionLine) -> PurchaseRequisitionLineStatus:
        requested = float(line.quantity_requested or 0.0)
        sourced = float(line.quantity_sourced or 0.0)
        if sourced <= 0:
            return PurchaseRequisitionLineStatus.OPEN
        if sourced >= requested:
            return PurchaseRequisitionLineStatus.FULLY_SOURCED
        return PurchaseRequisitionLineStatus.PARTIALLY_SOURCED

    def _refresh_requisition_status(self, requisition: PurchaseRequisition) -> None:
        lines = self._requisition_line_repo.list_for_requisition(requisition.id)
        if not lines:
            return
        if all(line.status == PurchaseRequisitionLineStatus.FULLY_SOURCED for line in lines):
            next_status = PurchaseRequisitionStatus.FULLY_SOURCED
        else:
            any_sourced = any(float(line.quantity_sourced or 0.0) > 0 for line in lines)
            next_status = PurchaseRequisitionStatus.PARTIALLY_SOURCED if any_sourced else requisition.status
        if next_status == requisition.status:
            return
        validate_transition(
            current_status=requisition.status.value,
            next_status=next_status.value,
            transitions=REQUISITION_STATUS_TRANSITIONS,
        )
        requisition.status = next_status
        requisition.updated_at = datetime.now(timezone.utc)
        self._requisition_repo.update(requisition)

    def _adjust_on_order_balance(
        self,
        *,
        organization_id: str,
        item: StockItem,
        storeroom_id: str,
        uom: str,
        delta: float,
        effective_at: datetime,
    ) -> None:
        if delta == 0:
            return
        delta_in_stock_uom = convert_item_quantity(
            item,
            float(delta),
            from_uom=uom,
            to_uom=item.stock_uom,
            label="Purchase-order line UOM",
        )
        balance = self._balance_repo.get_for_stock_position(organization_id, item.id, storeroom_id)
        is_new_balance = balance is None
        if balance is None:
            balance = StockBalance.create(
                organization_id=organization_id,
                stock_item_id=item.id,
                storeroom_id=storeroom_id,
                uom=item.stock_uom,
            )
        new_on_order = float(balance.on_order_qty or 0.0) + float(delta_in_stock_uom)
        if new_on_order < 0:
            raise ValidationError("On-order quantity cannot become negative.", code="INVENTORY_NEGATIVE_ON_ORDER")
        balance.on_order_qty = new_on_order
        balance.uom = item.stock_uom
        balance.updated_at = effective_at
        if is_new_balance:
            self._balance_repo.add(balance)
        else:
            self._balance_repo.update(balance)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.manage", operation_label=operation_label)

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.read", operation_label=operation_label)

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise ValidationError("No active organization is selected.", code="ORG_ACTIVE_MISSING")
        return organization


__all__ = [
    "PurchasingSupportMixin",
    "build_purchase_order_number",
    "build_receipt_number",
    "normalize_currency_code",
]
