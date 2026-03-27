from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.inventory_procurement.domain import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderLineStatus,
    PurchaseOrderStatus,
    PurchaseRequisition,
    PurchaseRequisitionLine,
    PurchaseRequisitionLineStatus,
    PurchaseRequisitionStatus,
    ReceiptHeader,
    ReceiptLine,
)
from core.modules.inventory_procurement.interfaces import (
    PurchaseOrderLineRepository,
    PurchaseOrderRepository,
    PurchaseRequisitionLineRepository,
    PurchaseRequisitionRepository,
    ReceiptHeaderRepository,
    ReceiptLineRepository,
    StockBalanceRepository,
)
from core.modules.inventory_procurement.services.inventory import InventoryService
from core.modules.inventory_procurement.services.item_master import ItemMasterService
from core.modules.inventory_procurement.services.reference_service import InventoryReferenceService
from core.modules.inventory_procurement.services.stock_control import StockControlService
from core.modules.inventory_procurement.support import (
    PURCHASE_ORDER_STATUS_TRANSITIONS,
    REQUISITION_STATUS_TRANSITIONS,
    convert_item_quantity,
    normalize_nonnegative_quantity,
    normalize_optional_text,
    normalize_positive_quantity,
    normalize_uom,
    resolve_item_uom_factor,
    validate_transition,
)
from core.platform.approval import ApprovalService
from core.platform.approval.domain import ApprovalRequest
from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository
from core.platform.common.models import Organization
from core.platform.notifications.domain_events import domain_events


def _build_purchase_order_number() -> str:
    return f"INV-PO-{uuid4().hex[:10].upper()}"


def _build_receipt_number() -> str:
    return f"INV-RCV-{uuid4().hex[:10].upper()}"


def _normalize_currency_code(value: str | None, *, fallback: str = "") -> str:
    normalized = normalize_optional_text(value).upper() or normalize_optional_text(fallback).upper()
    if not normalized:
        raise ValidationError("Currency code is required.", code="INVENTORY_CURRENCY_REQUIRED")
    return normalized


class PurchasingService:
    def __init__(
        self,
        session: Session,
        purchase_order_repo: PurchaseOrderRepository,
        purchase_order_line_repo: PurchaseOrderLineRepository,
        receipt_header_repo: ReceiptHeaderRepository,
        receipt_line_repo: ReceiptLineRepository,
        *,
        requisition_repo: PurchaseRequisitionRepository,
        requisition_line_repo: PurchaseRequisitionLineRepository,
        balance_repo: StockBalanceRepository,
        organization_repo: OrganizationRepository,
        reference_service: InventoryReferenceService,
        inventory_service: InventoryService,
        item_service: ItemMasterService,
        stock_service: StockControlService,
        approval_service: ApprovalService,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._purchase_order_repo = purchase_order_repo
        self._purchase_order_line_repo = purchase_order_line_repo
        self._receipt_header_repo = receipt_header_repo
        self._receipt_line_repo = receipt_line_repo
        self._requisition_repo = requisition_repo
        self._requisition_line_repo = requisition_line_repo
        self._balance_repo = balance_repo
        self._organization_repo = organization_repo
        self._reference_service = reference_service
        self._inventory_service = inventory_service
        self._item_service = item_service
        self._stock_service = stock_service
        self._approval_service = approval_service
        self._user_session = user_session
        self._audit_service = audit_service

    def list_purchase_orders(
        self,
        *,
        status: str | None = None,
        site_id: str | None = None,
        supplier_party_id: str | None = None,
        limit: int = 200,
    ) -> list[PurchaseOrder]:
        self._require_read("list purchase orders")
        organization = self._active_organization()
        return self._purchase_order_repo.list_for_organization(
            organization.id,
            status=normalize_optional_text(status).upper() or None,
            site_id=normalize_optional_text(site_id) or None,
            supplier_party_id=normalize_optional_text(supplier_party_id) or None,
            limit=max(1, int(limit or 200)),
        )

    def get_purchase_order(self, purchase_order_id: str) -> PurchaseOrder:
        self._require_read("view purchase order")
        organization = self._active_organization()
        purchase_order = self._purchase_order_repo.get(purchase_order_id)
        if purchase_order is None or purchase_order.organization_id != organization.id:
            raise NotFoundError(
                "Purchase order not found in the active organization.",
                code="INVENTORY_PURCHASE_ORDER_NOT_FOUND",
            )
        return purchase_order

    def list_purchase_order_lines(self, purchase_order_id: str) -> list[PurchaseOrderLine]:
        purchase_order = self.get_purchase_order(purchase_order_id)
        return self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)

    def list_receipts(
        self,
        *,
        purchase_order_id: str | None = None,
        limit: int = 200,
    ) -> list[ReceiptHeader]:
        self._require_read("list receipts")
        organization = self._active_organization()
        return self._receipt_header_repo.list_for_organization(
            organization.id,
            purchase_order_id=normalize_optional_text(purchase_order_id) or None,
            limit=max(1, int(limit or 200)),
        )

    def get_receipt(self, receipt_id: str) -> ReceiptHeader:
        self._require_read("view receipt")
        organization = self._active_organization()
        receipt = self._receipt_header_repo.get(receipt_id)
        if receipt is None or receipt.organization_id != organization.id:
            raise NotFoundError("Receipt not found in the active organization.", code="INVENTORY_RECEIPT_NOT_FOUND")
        return receipt

    def list_receipt_lines(self, receipt_id: str) -> list[ReceiptLine]:
        receipt = self.get_receipt(receipt_id)
        return self._receipt_line_repo.list_for_receipt(receipt.id)

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
            po_number=_build_purchase_order_number(),
            site_id=site.id,
            supplier_party_id=supplier.id,
            currency_code=_normalize_currency_code(currency_code, fallback=getattr(site, "currency_code", "")),
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
        request = self._approval_service.request_change(
            request_type="purchase_order.submit",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            project_id=None,
            payload={
                "purchase_order_id": purchase_order.id,
                "po_number": purchase_order.po_number,
                "site_id": purchase_order.site_id,
                "supplier_party_id": purchase_order.supplier_party_id,
                "source_requisition_id": purchase_order.source_requisition_id or "",
                "line_count": len(lines),
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
        purchase_order.currency_code = _normalize_currency_code(currency_code, fallback=getattr(site, "currency_code", ""))
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

    def post_receipt(
        self,
        purchase_order_id: str,
        *,
        receipt_lines: list[dict],
        receipt_date: datetime | None = None,
        supplier_delivery_reference: str = "",
        notes: str = "",
    ) -> ReceiptHeader:
        self._require_manage("post receipt")
        purchase_order = self.get_purchase_order(purchase_order_id)
        if purchase_order.status not in {
            PurchaseOrderStatus.APPROVED,
            PurchaseOrderStatus.SENT,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
        }:
            raise ValidationError(
                "Purchase order is not open for receiving.",
                code="INVENTORY_PURCHASE_ORDER_RECEIVING_STATUS_INVALID",
            )
        order_lines = {line.id: line for line in self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)}
        if not receipt_lines:
            raise ValidationError("At least one receipt line is required.", code="INVENTORY_RECEIPT_LINES_REQUIRED")
        principal = self._user_session.principal if self._user_session is not None else None
        effective_receipt_date = receipt_date or datetime.now(timezone.utc)
        receipt = ReceiptHeader.create(
            organization_id=purchase_order.organization_id,
            receipt_number=_build_receipt_number(),
            purchase_order_id=purchase_order.id,
            received_site_id=purchase_order.site_id,
            supplier_party_id=purchase_order.supplier_party_id,
            receipt_date=effective_receipt_date,
            supplier_delivery_reference=normalize_optional_text(supplier_delivery_reference),
            received_by_user_id=getattr(principal, "user_id", None),
            received_by_username=str(getattr(principal, "username", "") or ""),
            notes=normalize_optional_text(notes),
        )
        created_receipt_lines: list[ReceiptLine] = []
        created_transactions = []
        touched_balance_ids: set[str] = set()
        try:
            self._receipt_header_repo.add(receipt)
            self._session.flush()
            for index, payload in enumerate(receipt_lines, start=1):
                line_id = normalize_optional_text(str(payload.get("purchase_order_line_id") or ""))
                if not line_id:
                    raise ValidationError("Receipt line purchase_order_line_id is required.", code="INVENTORY_RECEIPT_LINE_ID_REQUIRED")
                po_line = order_lines.get(line_id)
                if po_line is None:
                    raise ValidationError("Receipt line does not belong to the selected purchase order.", code="INVENTORY_RECEIPT_LINE_SCOPE_INVALID")
                accepted = normalize_nonnegative_quantity(payload.get("quantity_accepted"), label="Accepted quantity")
                rejected = normalize_nonnegative_quantity(payload.get("quantity_rejected"), label="Rejected quantity")
                processed = accepted + rejected
                if processed <= 0:
                    raise ValidationError("Receipt line must accept or reject a positive quantity.", code="INVENTORY_RECEIPT_QUANTITY_REQUIRED")
                outstanding = self._line_outstanding_qty(po_line)
                if processed > outstanding:
                    raise ValidationError("Receipt quantity exceeds the remaining open quantity.", code="INVENTORY_RECEIPT_EXCEEDS_OPEN_QTY")
                unit_cost = normalize_nonnegative_quantity(payload.get("unit_cost", po_line.unit_price), label="Receipt unit cost")
                receipt_line = ReceiptLine.create(
                    receipt_header_id=receipt.id,
                    purchase_order_line_id=po_line.id,
                    line_number=index,
                    stock_item_id=po_line.stock_item_id,
                    storeroom_id=po_line.destination_storeroom_id,
                    quantity_accepted=accepted,
                    quantity_rejected=rejected,
                    uom=po_line.uom,
                    unit_cost=unit_cost,
                    notes=normalize_optional_text(str(payload.get("notes") or "")),
                )
                self._receipt_line_repo.add(receipt_line)
                created_receipt_lines.append(receipt_line)
                po_line.quantity_received += accepted
                po_line.quantity_rejected += rejected
                po_line.status = self._resolve_purchase_order_line_status(po_line, treat_open=True)
                self._purchase_order_line_repo.update(po_line)
                if accepted > 0:
                    transaction = self._stock_service.post_adjustment(
                        stock_item_id=po_line.stock_item_id,
                        storeroom_id=po_line.destination_storeroom_id,
                        quantity=accepted,
                        direction="INCREASE",
                        uom=po_line.uom,
                        unit_cost=unit_cost,
                        transaction_at=effective_receipt_date,
                        reference_type="inventory_receipt",
                        reference_id=receipt_line.id,
                        notes=receipt_line.notes,
                        commit=False,
                    )
                    created_transactions.append(transaction)
                    balance = self._balance_repo.get_for_stock_position(
                        purchase_order.organization_id,
                        po_line.stock_item_id,
                        po_line.destination_storeroom_id,
                    )
                    if balance is not None:
                        touched_balance_ids.add(balance.id)
                self._adjust_on_order_balance(
                    organization_id=purchase_order.organization_id,
                    item=self._item_service.get_item_for_internal_use(po_line.stock_item_id),
                    storeroom_id=po_line.destination_storeroom_id,
                    uom=po_line.uom,
                    delta=-processed,
                    effective_at=effective_receipt_date,
                )
                balance = self._balance_repo.get_for_stock_position(
                    purchase_order.organization_id,
                    po_line.stock_item_id,
                    po_line.destination_storeroom_id,
                )
                if balance is not None:
                    touched_balance_ids.add(balance.id)
            purchase_order.status = self._resolve_purchase_order_receiving_status(
                self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)
            )
            purchase_order.updated_at = effective_receipt_date
            self._purchase_order_repo.update(purchase_order)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_receipt.post",
            entity_type="inventory_receipt",
            entity_id=receipt.id,
            details={
                "receipt_number": receipt.receipt_number,
                "purchase_order_id": receipt.purchase_order_id,
                "supplier_delivery_reference": receipt.supplier_delivery_reference,
                "line_count": str(len(created_receipt_lines)),
            },
        )
        for transaction in created_transactions:
            record_audit(
                self,
                action="inventory_stock_transaction.post",
                entity_type="inventory_stock_transaction",
                entity_id=transaction.id,
                details={
                    "transaction_number": transaction.transaction_number,
                    "stock_item_id": transaction.stock_item_id,
                    "storeroom_id": transaction.storeroom_id,
                    "transaction_type": transaction.transaction_type.value,
                    "quantity": str(transaction.quantity),
                    "uom": transaction.uom,
                    "reference_id": transaction.reference_id,
                },
            )
        domain_events.inventory_receipts_changed.emit(receipt.id)
        domain_events.inventory_purchase_orders_changed.emit(purchase_order.id)
        for balance_id in touched_balance_ids:
            domain_events.inventory_balances_changed.emit(balance_id)
        return receipt

    def apply_submitted_purchase_order_approval(self, request: ApprovalRequest) -> None:
        purchase_order = self._purchase_order_repo.get(request.entity_id)
        if purchase_order is None:
            raise NotFoundError("Purchase order not found.", code="INVENTORY_PURCHASE_ORDER_NOT_FOUND")
        if purchase_order.approval_request_id != request.id:
            raise ValidationError("Approval request does not match the purchase order.", code="INVENTORY_PURCHASE_ORDER_APPROVAL_MISMATCH")
        current_status = purchase_order.status.value
        if current_status not in {PurchaseOrderStatus.SUBMITTED.value, PurchaseOrderStatus.UNDER_REVIEW.value}:
            raise ValidationError("Purchase order is not awaiting approval.", code="INVENTORY_PURCHASE_ORDER_STATUS_INVALID")
        validate_transition(
            current_status=current_status,
            next_status=PurchaseOrderStatus.APPROVED.value,
            transitions=PURCHASE_ORDER_STATUS_TRANSITIONS,
        )
        effective_at = datetime.now(timezone.utc)
        purchase_order.status = PurchaseOrderStatus.APPROVED
        purchase_order.approved_at = effective_at
        purchase_order.updated_at = effective_at
        self._purchase_order_repo.update(purchase_order)
        lines = self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)
        touched_requisition_ids: set[str] = set()
        touched_balance_ids: set[str] = set()
        for line in lines:
            line.status = PurchaseOrderLineStatus.OPEN
            self._purchase_order_line_repo.update(line)
            self._adjust_on_order_balance(
                organization_id=purchase_order.organization_id,
                item=self._item_service.get_item_for_internal_use(line.stock_item_id),
                storeroom_id=line.destination_storeroom_id,
                uom=line.uom,
                delta=line.quantity_ordered,
                effective_at=effective_at,
            )
            balance = self._balance_repo.get_for_stock_position(
                purchase_order.organization_id,
                line.stock_item_id,
                line.destination_storeroom_id,
            )
            if balance is not None:
                touched_balance_ids.add(balance.id)
            if line.source_requisition_line_id:
                requisition_line = self._require_requisition_line(line.source_requisition_line_id)
                item = self._item_service.get_item_for_internal_use(line.stock_item_id)
                sourced_qty = convert_item_quantity(
                    item,
                    float(line.quantity_ordered or 0.0),
                    from_uom=line.uom,
                    to_uom=requisition_line.uom,
                    label="Purchase-order line UOM",
                )
                new_sourced_qty = float(requisition_line.quantity_sourced or 0.0) + sourced_qty
                if new_sourced_qty > float(requisition_line.quantity_requested or 0.0):
                    raise ValidationError(
                        "Approved purchase order would oversource the requisition line.",
                        code="INVENTORY_REQUISITION_LINE_OVERSOURCED",
                    )
                requisition_line.quantity_sourced = new_sourced_qty
                requisition_line.status = self._resolve_requisition_line_status(requisition_line)
                self._requisition_line_repo.update(requisition_line)
                touched_requisition_ids.add(requisition_line.purchase_requisition_id)
        for requisition_id in touched_requisition_ids:
            requisition = self._requisition_repo.get(requisition_id)
            if requisition is None:
                continue
            self._refresh_requisition_status(requisition)
        record_audit(
            self,
            action="inventory_purchase_order.approve",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            details={
                "po_number": purchase_order.po_number,
                "approval_request_id": request.id,
            },
        )
        domain_events.inventory_purchase_orders_changed.emit(purchase_order.id)
        for requisition_id in touched_requisition_ids:
            domain_events.inventory_requisitions_changed.emit(requisition_id)
        for balance_id in touched_balance_ids:
            domain_events.inventory_balances_changed.emit(balance_id)

    def apply_submitted_purchase_order_rejection(self, request: ApprovalRequest) -> None:
        purchase_order = self._purchase_order_repo.get(request.entity_id)
        if purchase_order is None:
            raise NotFoundError("Purchase order not found.", code="INVENTORY_PURCHASE_ORDER_NOT_FOUND")
        if purchase_order.approval_request_id != request.id:
            raise ValidationError("Approval request does not match the purchase order.", code="INVENTORY_PURCHASE_ORDER_APPROVAL_MISMATCH")
        current_status = purchase_order.status.value
        if current_status not in {PurchaseOrderStatus.SUBMITTED.value, PurchaseOrderStatus.UNDER_REVIEW.value}:
            raise ValidationError("Purchase order is not awaiting approval.", code="INVENTORY_PURCHASE_ORDER_STATUS_INVALID")
        validate_transition(
            current_status=current_status,
            next_status=PurchaseOrderStatus.REJECTED.value,
            transitions=PURCHASE_ORDER_STATUS_TRANSITIONS,
        )
        purchase_order.status = PurchaseOrderStatus.REJECTED
        purchase_order.updated_at = datetime.now(timezone.utc)
        self._purchase_order_repo.update(purchase_order)
        for line in self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id):
            line.status = PurchaseOrderLineStatus.CANCELLED
            self._purchase_order_line_repo.update(line)
        record_audit(
            self,
            action="inventory_purchase_order.reject",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            details={
                "po_number": purchase_order.po_number,
                "approval_request_id": request.id,
            },
        )
        domain_events.inventory_purchase_orders_changed.emit(purchase_order.id)

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
        item,
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
        item,
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
            from core.modules.inventory_procurement.domain import StockBalance

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


__all__ = ["PurchasingService"]
