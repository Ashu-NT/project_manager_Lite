from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError

from core.modules.inventory_procurement.domain import PurchaseOrder, PurchaseOrderLine, PurchaseOrderLineStatus, PurchaseOrderStatus
from core.modules.inventory_procurement.services.procurement.purchasing_support import build_purchase_order_number, normalize_currency_code
from core.modules.inventory_procurement.support import (
    PURCHASE_ORDER_STATUS_TRANSITIONS,
    normalize_nonnegative_quantity,
    normalize_optional_text,
    normalize_positive_quantity,
    normalize_uom,
    resolve_item_uom_factor,
    validate_transition,
)
from src.core.platform.audit.helpers import record_audit
from src.core.platform.common.exceptions import ConcurrencyError, ValidationError
from src.core.platform.notifications.domain_events import domain_events


class PurchasingLifecycleMixin:
    def create_purchase_order(
        self,
        *,
        site_id: str,
        supplier_party_id: str,
        currency_code: str | None = None,
        source_requisition_id: str | None = None,
        order_date: date | None = None,
        expected_delivery_date: date | None = None,
        supplier_reference: str = "",
        notes: str = "",
        po_number: str | None = None,
    ) -> PurchaseOrder:
        self._require_manage("create purchase order")
        organization = self._active_organization()
        site = self._reference_service.get_site(site_id)
        if site.organization_id != organization.id or not site.is_active:
            raise ValidationError("Selected site must be active in the current organization.", code="INVENTORY_SITE_SCOPE_INVALID")
        supplier = self._reference_service.get_party(supplier_party_id)
        if supplier.organization_id != organization.id or not supplier.is_active:
            raise ValidationError("Selected supplier must be active in the current organization.", code="INVENTORY_SUPPLIER_SCOPE_INVALID")
        requisition = self._validate_source_requisition(source_requisition_id, organization.id)
        purchase_order = PurchaseOrder.create(
            organization_id=organization.id,
            po_number=normalize_optional_text(po_number) or build_purchase_order_number(),
            site_id=site.id,
            supplier_party_id=supplier.id,
            currency_code=normalize_currency_code(currency_code, fallback=getattr(site, "currency_code", "")),
            source_requisition_id=requisition.id if requisition is not None else None,
            order_date=order_date,
            expected_delivery_date=expected_delivery_date,
            supplier_reference=normalize_optional_text(supplier_reference),
            notes=normalize_optional_text(notes),
        )
        try:
            self._purchase_order_repo.add(purchase_order)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Purchase order number already exists.", code="INVENTORY_PURCHASE_ORDER_NUMBER_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_purchase_order.create",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            details={
                "po_number": purchase_order.po_number,
                "site_id": purchase_order.site_id,
                "supplier_party_id": purchase_order.supplier_party_id,
                "source_requisition_id": purchase_order.source_requisition_id or "",
            },
        )
        domain_events.inventory_purchase_orders_changed.emit(purchase_order.id)
        return purchase_order

    def add_purchase_order_line(
        self,
        purchase_order_id: str,
        *,
        stock_item_id: str,
        destination_storeroom_id: str,
        quantity_ordered: float,
        uom: str | None = None,
        unit_price: float = 0.0,
        expected_delivery_date: date | None = None,
        description: str = "",
        source_requisition_line_id: str | None = None,
        notes: str = "",
    ) -> PurchaseOrderLine:
        self._require_manage("add purchase order line")
        purchase_order = self._require_draft_purchase_order(purchase_order_id)
        item = self._item_service.get_item(stock_item_id)
        if item.organization_id != purchase_order.organization_id or not item.is_active:
            raise ValidationError("Purchase-order item must be active in the current organization.", code="INVENTORY_PO_ITEM_SCOPE_INVALID")
        if not item.is_purchase_allowed:
            raise ValidationError("Purchase-order item is not enabled for purchasing.", code="INVENTORY_ITEM_PURCHASE_FORBIDDEN")
        storeroom = self._inventory_service.get_storeroom(destination_storeroom_id)
        if storeroom.organization_id != purchase_order.organization_id or not storeroom.is_active:
            raise ValidationError("Destination storeroom must be active in the current organization.", code="INVENTORY_PO_STOREROOM_SCOPE_INVALID")
        if storeroom.site_id != purchase_order.site_id:
            raise ValidationError("Destination storeroom must belong to the purchase-order site.", code="INVENTORY_PO_SITE_STOREROOM_MISMATCH")
        if not storeroom.allows_receiving:
            raise ValidationError("Destination storeroom does not allow receiving.", code="INVENTORY_RECEIVING_FORBIDDEN")
        normalized_uom = normalize_uom(uom or item.stock_uom, label="Purchase-order line UOM")
        resolve_item_uom_factor(item, normalized_uom, label="Purchase-order line UOM")
        source_line = self._validate_source_requisition_line(
            purchase_order=purchase_order,
            item=item,
            source_requisition_line_id=source_requisition_line_id,
            quantity_ordered=quantity_ordered,
            quantity_ordered_uom=normalized_uom,
        )
        next_line_number = len(self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)) + 1
        line = PurchaseOrderLine.create(
            purchase_order_id=purchase_order.id,
            line_number=next_line_number,
            stock_item_id=item.id,
            destination_storeroom_id=storeroom.id,
            description=normalize_optional_text(description) or item.name,
            quantity_ordered=normalize_positive_quantity(quantity_ordered, label="Purchase-order quantity"),
            uom=normalized_uom,
            unit_price=normalize_nonnegative_quantity(unit_price, label="Unit price"),
            expected_delivery_date=expected_delivery_date,
            source_requisition_line_id=source_line.id if source_line is not None else None,
            notes=normalize_optional_text(notes),
        )
        try:
            self._purchase_order_line_repo.add(line)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Purchase order line already exists.", code="INVENTORY_PURCHASE_ORDER_LINE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_purchase_order_line.create",
            entity_type="purchase_order_line",
            entity_id=line.id,
            details={
                "purchase_order_id": purchase_order.id,
                "line_number": str(line.line_number),
                "stock_item_id": line.stock_item_id,
                "destination_storeroom_id": line.destination_storeroom_id,
                "source_requisition_line_id": line.source_requisition_line_id or "",
            },
        )
        domain_events.inventory_purchase_orders_changed.emit(purchase_order.id)
        return line

    def submit_purchase_order(self, purchase_order_id: str, *, note: str = "") -> PurchaseOrder:
        self._require_manage("submit purchase order")
        purchase_order = self._require_draft_purchase_order(purchase_order_id)
        lines = self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)
        if not lines:
            raise ValidationError(
                "Purchase order must have at least one line before submission.",
                code="INVENTORY_PURCHASE_ORDER_LINES_REQUIRED",
            )

        site = self._reference_service.get_site(purchase_order.site_id)
        supplier = self._reference_service.get_party(purchase_order.supplier_party_id)
        total_amount = sum((line.quantity_ordered or 0.0) * (line.unit_price or 0.0) for line in lines)

        request = self._approval_service.request_change(
            request_type="purchase_order.submit",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            project_id=None,
            payload={
                "purchase_order_id": purchase_order.id,
                "po_number": purchase_order.po_number,
                "site_id": purchase_order.site_id,
                "site_name": getattr(site, "name", ""),
                "supplier_party_id": purchase_order.supplier_party_id,
                "supplier_name": getattr(supplier, "party_name", ""),
                "source_requisition_id": purchase_order.source_requisition_id or "",
                "line_count": len(lines),
                "total_amount": round(total_amount, 2),
                "currency_code": purchase_order.currency_code,
                "order_date": purchase_order.order_date.isoformat() if purchase_order.order_date else "",
                "expected_delivery_date": purchase_order.expected_delivery_date.isoformat() if purchase_order.expected_delivery_date else "",
            },
            commit=False,
        )
        validate_transition(
            current_status=purchase_order.status.value,
            next_status=PurchaseOrderStatus.SUBMITTED.value,
            transitions=PURCHASE_ORDER_STATUS_TRANSITIONS,
        )
        purchase_order.status = PurchaseOrderStatus.SUBMITTED
        purchase_order.approval_request_id = request.id
        purchase_order.submitted_at = datetime.now(timezone.utc)
        purchase_order.updated_at = purchase_order.submitted_at
        self._purchase_order_repo.update(purchase_order)
        self._session.commit()
        record_audit(
            self,
            action="inventory_purchase_order.submit",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            details={
                "po_number": purchase_order.po_number,
                "approval_request_id": request.id,
                "note": normalize_optional_text(note),
            },
        )
        domain_events.approvals_changed.emit(request.id)
        domain_events.inventory_purchase_orders_changed.emit(purchase_order.id)
        return purchase_order

    def update_purchase_order(
        self,
        purchase_order_id: str,
        *,
        site_id: str | None = None,
        supplier_party_id: str | None = None,
        currency_code: str | None = None,
        source_requisition_id: str | None = None,
        expected_delivery_date: date | None = None,
        supplier_reference: str | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> PurchaseOrder:
        self._require_manage("update purchase order")
        purchase_order = self._require_draft_purchase_order(purchase_order_id)
        if expected_version is not None and purchase_order.version != expected_version:
            raise ConcurrencyError(
                "Purchase order changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        organization = self._active_organization()
        next_site_id = normalize_optional_text(site_id) or purchase_order.site_id
        next_supplier_id = normalize_optional_text(supplier_party_id) or purchase_order.supplier_party_id
        site = self._reference_service.get_site(next_site_id)
        if site.organization_id != organization.id or not site.is_active:
            raise ValidationError(
                "Selected site must be active in the current organization.",
                code="INVENTORY_SITE_SCOPE_INVALID",
            )
        supplier = self._reference_service.get_party(next_supplier_id)
        if supplier.organization_id != organization.id or not supplier.is_active:
            raise ValidationError(
                "Selected supplier must be active in the current organization.",
                code="INVENTORY_SUPPLIER_SCOPE_INVALID",
            )
        requisition = self._validate_source_requisition(source_requisition_id, organization.id)
        purchase_order.site_id = site.id
        purchase_order.supplier_party_id = supplier.id
        purchase_order.currency_code = normalize_currency_code(currency_code, fallback=getattr(site, "currency_code", ""))
        purchase_order.source_requisition_id = requisition.id if requisition is not None else None
        purchase_order.expected_delivery_date = expected_delivery_date
        if supplier_reference is not None:
            purchase_order.supplier_reference = normalize_optional_text(supplier_reference)
        if notes is not None:
            purchase_order.notes = normalize_optional_text(notes)
        purchase_order.updated_at = datetime.now(timezone.utc)
        try:
            self._purchase_order_repo.update(purchase_order)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_purchase_order.update",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            details={
                "po_number": purchase_order.po_number,
                "site_id": purchase_order.site_id,
                "supplier_party_id": purchase_order.supplier_party_id,
                "source_requisition_id": purchase_order.source_requisition_id or "",
            },
        )
        domain_events.inventory_purchase_orders_changed.emit(purchase_order.id)
        return purchase_order

    def cancel_purchase_order(
        self,
        purchase_order_id: str,
        *,
        note: str = "",
        expected_version: int | None = None,
    ) -> PurchaseOrder:
        self._require_manage("cancel purchase order")
        purchase_order = self._require_draft_purchase_order(purchase_order_id)
        if expected_version is not None and purchase_order.version != expected_version:
            raise ConcurrencyError(
                "Purchase order changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        validate_transition(
            current_status=purchase_order.status.value,
            next_status=PurchaseOrderStatus.CANCELLED.value,
            transitions=PURCHASE_ORDER_STATUS_TRANSITIONS,
        )
        effective_at = datetime.now(timezone.utc)
        purchase_order.status = PurchaseOrderStatus.CANCELLED
        purchase_order.cancelled_at = effective_at
        purchase_order.updated_at = effective_at
        lines = self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)
        for line in lines:
            line.status = PurchaseOrderLineStatus.CANCELLED
            self._purchase_order_line_repo.update(line)
        try:
            self._purchase_order_repo.update(purchase_order)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_purchase_order.cancel",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            details={
                "po_number": purchase_order.po_number,
                "note": normalize_optional_text(note),
            },
        )
        domain_events.inventory_purchase_orders_changed.emit(purchase_order.id)
        return purchase_order

    def send_purchase_order(
        self,
        purchase_order_id: str,
        *,
        note: str = "",
    ) -> PurchaseOrder:
        self._require_manage("send purchase order")
        purchase_order = self.get_purchase_order(purchase_order_id)
        validate_transition(
            current_status=purchase_order.status.value,
            next_status=PurchaseOrderStatus.SENT.value,
            transitions=PURCHASE_ORDER_STATUS_TRANSITIONS,
        )
        effective_at = datetime.now(timezone.utc)
        purchase_order.status = PurchaseOrderStatus.SENT
        purchase_order.sent_at = effective_at
        if purchase_order.order_date is None:
            purchase_order.order_date = effective_at.date()
        purchase_order.updated_at = effective_at
        try:
            self._purchase_order_repo.update(purchase_order)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_purchase_order.send",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            details={
                "po_number": purchase_order.po_number,
                "note": normalize_optional_text(note),
            },
        )
        domain_events.inventory_purchase_orders_changed.emit(purchase_order.id)
        return purchase_order

    def close_purchase_order(
        self,
        purchase_order_id: str,
        *,
        note: str = "",
    ) -> PurchaseOrder:
        self._require_manage("close purchase order")
        purchase_order = self.get_purchase_order(purchase_order_id)
        lines = self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)
        if not lines:
            raise ValidationError(
                "Purchase order must have at least one line before it can be closed.",
                code="INVENTORY_PURCHASE_ORDER_LINES_REQUIRED",
            )
        if not self._is_purchase_order_fully_processed(lines):
            raise ValidationError(
                "Purchase order still has open quantity and cannot be closed.",
                code="INVENTORY_PURCHASE_ORDER_NOT_FULLY_PROCESSED",
            )
        validate_transition(
            current_status=purchase_order.status.value,
            next_status=PurchaseOrderStatus.CLOSED.value,
            transitions=PURCHASE_ORDER_STATUS_TRANSITIONS,
        )
        effective_at = datetime.now(timezone.utc)
        purchase_order.status = PurchaseOrderStatus.CLOSED
        purchase_order.closed_at = effective_at
        purchase_order.updated_at = effective_at
        try:
            self._purchase_order_repo.update(purchase_order)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_purchase_order.close",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            details={
                "po_number": purchase_order.po_number,
                "note": normalize_optional_text(note),
            },
        )
        domain_events.inventory_purchase_orders_changed.emit(purchase_order.id)
        return purchase_order


__all__ = ["PurchasingLifecycleMixin"]
