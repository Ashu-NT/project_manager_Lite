from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from src.core.modules.inventory_procurement.application.common.support import (
    PURCHASE_ORDER_STATUS_TRANSITIONS,
    convert_item_quantity,
    normalize_optional_text,
    validate_receipt_tracking,
    validate_transition,
)
from src.core.modules.inventory_procurement.application.procurement.purchasing_support import (
    build_receipt_number,
)
from src.core.modules.inventory_procurement.domain.inventory.balance_events import (
    StockOnHandQuantityChanged,
    StockOnOrderQuantityChanged,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseOrderLineStatus,
    PurchaseOrderStatus,
    PurchaseRequisitionLineStatus,
    ReceiptHeader,
    ReceiptLine,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing_events import (
    InventoryPurchaseOrderApproved,
    InventoryPurchaseOrderReceivingAdvanced,
    InventoryPurchaseOrderRejected,
)
from src.core.modules.inventory_procurement.domain.procurement.requisition_events import (
    InventoryRequisitionSourcingAdvanced,
)
from src.core.modules.inventory_procurement.domain.procurement.receipt_events import (
    InventoryReceiptPosted,
)
from src.core.platform.domain.approval import ApprovalRequest
from src.core.platform.contract.models.approval.contracts import (
    ApprovalHandlerResult,
)
from src.core.platform.common.ids import generate_id
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext


class PurchasingReceivingMixin:
    def post_receipt(
        self,
        purchase_order_id: str,
        *,
        receipt_lines: list[dict],
        receipt_date: datetime | None = None,
        supplier_delivery_reference: str = "",
        notes: str = "",
        receipt_number: str | None = None,
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
        receipt = ReceiptHeader.create(
            organization_id=purchase_order.organization_id,
            receipt_number=receipt_number or build_receipt_number(),
            purchase_order_id=purchase_order.id,
            received_site_id=purchase_order.site_id,
            supplier_party_id=purchase_order.supplier_party_id,
            receipt_date=receipt_date,
            supplier_delivery_reference=supplier_delivery_reference,
            received_by_user_id=getattr(principal, "user_id", None),
            received_by_username=str(getattr(principal, "username", "") or ""),
            notes=notes,
        )
        effective_receipt_date = receipt.receipt_date or datetime.now(timezone.utc)
        created_receipt_lines: list[ReceiptLine] = []
        created_transactions = []
        final_lines_by_id = dict(order_lines)
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="post receipt"
        )

        with self._require_purchase_order_uow_factory().create(
            context=DomainEventContext(correlation_id=generate_id())
        ) as uow:
            receipt_header_repo, receipt_line_repo, stock_service = (
                self._require_receiving_collaborators_factory()(uow._session)
            )
            receipt_header_repo.add(receipt)
            uow._session.flush()
            for index, payload in enumerate(receipt_lines, start=1):
                line_id = normalize_optional_text(str(payload.get("purchase_order_line_id") or ""))
                if not line_id:
                    raise ValidationError(
                        "Receipt line purchase_order_line_id is required.",
                        code="INVENTORY_RECEIPT_LINE_ID_REQUIRED",
                    )
                po_line = order_lines.get(line_id)
                if po_line is None:
                    raise ValidationError(
                        "Receipt line does not belong to the selected purchase order.",
                        code="INVENTORY_RECEIPT_LINE_SCOPE_INVALID",
                    )
                item = self._item_service.get_item_for_internal_use(po_line.stock_item_id)
                storeroom = self._inventory_service.get_storeroom(po_line.destination_storeroom_id)
                if (
                    storeroom.requires_supplier_reference_for_receipt
                    and not receipt.supplier_delivery_reference
                ):
                    raise ValidationError(
                        "Selected storeroom requires a supplier delivery reference for receipts.",
                        code="INVENTORY_RECEIPT_REFERENCE_REQUIRED",
                    )
                receipt_line = ReceiptLine.create(
                    receipt_header_id=receipt.id,
                    purchase_order_line_id=po_line.id,
                    line_number=index,
                    stock_item_id=po_line.stock_item_id,
                    storeroom_id=po_line.destination_storeroom_id,
                    quantity_accepted=payload.get("quantity_accepted"),
                    quantity_rejected=payload.get("quantity_rejected", 0.0),
                    uom=po_line.uom,
                    unit_cost=payload.get("unit_cost", po_line.unit_price),
                    lot_number=str(payload.get("lot_number") or ""),
                    serial_number=str(payload.get("serial_number") or ""),
                    expiry_date=payload.get("expiry_date"),
                    notes=str(payload.get("notes") or ""),
                )
                accepted = receipt_line.quantity_accepted
                rejected = receipt_line.quantity_rejected
                processed = accepted + rejected
                outstanding = self._line_outstanding_qty(po_line)
                if processed > outstanding:
                    raise ValidationError(
                        "Receipt quantity exceeds the remaining open quantity.",
                        code="INVENTORY_RECEIPT_EXCEEDS_OPEN_QTY",
                    )
                validate_receipt_tracking(
                    item=item,
                    accepted_quantity=accepted,
                    lot_number=receipt_line.lot_number,
                    serial_number=receipt_line.serial_number,
                    expiry_date=receipt_line.expiry_date,
                    receipt_date=effective_receipt_date,
                )
                receipt_line_repo.add(receipt_line)
                created_receipt_lines.append(receipt_line)
                next_received = float(po_line.quantity_received or 0.0) + accepted
                next_rejected = float(po_line.quantity_rejected or 0.0) + rejected
                next_processed = next_received + next_rejected
                if next_processed <= 0:
                    next_status = PurchaseOrderLineStatus.OPEN
                elif next_processed >= float(po_line.quantity_ordered or 0.0):
                    next_status = PurchaseOrderLineStatus.FULLY_RECEIVED
                else:
                    next_status = PurchaseOrderLineStatus.PARTIALLY_RECEIVED
                po_line = replace(
                    po_line,
                    quantity_received=next_received,
                    quantity_rejected=next_rejected,
                    status=next_status,
                )
                uow.purchase_order_lines.update(po_line)
                final_lines_by_id[po_line.id] = po_line
                # Delta is computed as (resulting - previous), never re-derived from the
                # line-UOM `accepted`/`processed` values -- avoids duplicating
                # `post_adjustment`'s/`_adjust_on_order_balance`'s own UOM-to-stock-UOM
                # conversion math (P31B §5).
                previous_balance = uow.balances.get_for_stock_position(
                    purchase_order.organization_id,
                    po_line.stock_item_id,
                    po_line.destination_storeroom_id,
                )
                previous_on_hand = float(previous_balance.on_hand_qty) if previous_balance else 0.0
                previous_on_order = float(previous_balance.on_order_qty) if previous_balance else 0.0
                if accepted > 0:
                    transaction = stock_service.post_adjustment(
                        stock_item_id=po_line.stock_item_id,
                        storeroom_id=po_line.destination_storeroom_id,
                        quantity=accepted,
                        direction="INCREASE",
                        uom=po_line.uom,
                        unit_cost=receipt_line.unit_cost,
                        transaction_at=effective_receipt_date,
                        reference_type="inventory_receipt",
                        reference_id=receipt_line.id,
                        notes=receipt_line.notes,
                        commit=False,
                    )
                    created_transactions.append(transaction)
                    balance = uow.balances.get_for_stock_position(
                        purchase_order.organization_id,
                        po_line.stock_item_id,
                        po_line.destination_storeroom_id,
                    )
                    if balance is not None:
                        uow.record_event(
                            StockOnHandQuantityChanged(
                                tenant_id=tenant_id,
                                organization_id=purchase_order.organization_id,
                                balance_id=balance.id,
                                stock_item_id=balance.stock_item_id,
                                storeroom_id=balance.storeroom_id,
                                quantity_delta=float(balance.on_hand_qty) - previous_on_hand,
                                resulting_quantity=balance.on_hand_qty,
                                occurred_at=effective_receipt_date,
                            )
                        )
                self._adjust_on_order_balance(
                    organization_id=purchase_order.organization_id,
                    item=self._item_service.get_item_for_internal_use(po_line.stock_item_id),
                    storeroom_id=po_line.destination_storeroom_id,
                    uom=po_line.uom,
                    delta=-processed,
                    effective_at=effective_receipt_date,
                    balance_repo=uow.balances,
                )
                balance = uow.balances.get_for_stock_position(
                    purchase_order.organization_id,
                    po_line.stock_item_id,
                    po_line.destination_storeroom_id,
                )
                if balance is not None:
                    if processed > 0:
                        uow.record_event(
                            StockOnOrderQuantityChanged(
                                tenant_id=tenant_id,
                                organization_id=purchase_order.organization_id,
                                balance_id=balance.id,
                                stock_item_id=balance.stock_item_id,
                                storeroom_id=balance.storeroom_id,
                                quantity_delta=float(balance.on_order_qty) - previous_on_order,
                                resulting_quantity=balance.on_order_qty,
                                occurred_at=effective_receipt_date,
                            )
                        )
            resulting_lines = list(final_lines_by_id.values())
            resulting_status = self._resolve_purchase_order_receiving_status(resulting_lines)
            purchase_order = replace(
                purchase_order,
                status=resulting_status,
                updated_at=max(
                    effective_receipt_date,
                    purchase_order.updated_at or effective_receipt_date,
                ),
            )
            uow.purchase_orders.update(purchase_order)
            self._enqueue_purchase_order_financial_events(purchase_order, resulting_lines)
            self._enqueue_receipt_financial_events(
                purchase_order=purchase_order,
                receipt=receipt,
                receipt_lines=created_receipt_lines,
            )
            record_activity(
                uow,
                action="inventory_receipt.post",
                entity_type="inventory_receipt",
                entity_id=receipt.id,
                module="inventory",
                details={
                    "receipt_number": receipt.receipt_number,
                    "purchase_order_id": receipt.purchase_order_id,
                    "supplier_delivery_reference": receipt.supplier_delivery_reference,
                    "line_count": str(len(created_receipt_lines)),
                },
                commit=False,
            )
            for transaction in created_transactions:
                record_activity(
                    uow,
                    action="inventory_stock_transaction.post",
                    entity_type="inventory_stock_transaction",
                    entity_id=transaction.id,
                    module="inventory",
                    details={
                        "transaction_number": transaction.transaction_number,
                        "stock_item_id": transaction.stock_item_id,
                        "storeroom_id": transaction.storeroom_id,
                        "transaction_type": transaction.transaction_type.value,
                        "quantity": str(transaction.quantity),
                        "uom": transaction.uom,
                        "reference_id": transaction.reference_id,
                    },
                    commit=False,
                )
            record_audit_entry(
                uow,
                operation="create",
                entity_type="inventory_receipt",
                entity_id=receipt.id,
                module="inventory",
                severity="low",
                metadata={
                    "receipt_number": receipt.receipt_number,
                    "purchase_order_id": receipt.purchase_order_id,
                    "line_count": str(len(created_receipt_lines)),
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                InventoryPurchaseOrderReceivingAdvanced(
                    tenant_id=tenant_id,
                    organization_id=purchase_order.organization_id,
                    purchase_order_id=purchase_order.id,
                    resulting_status=resulting_status.value,
                    occurred_at=effective_receipt_date,
                )
            )
            uow.record_event(
                InventoryReceiptPosted(
                    tenant_id=tenant_id,
                    organization_id=purchase_order.organization_id,
                    receipt_id=receipt.id,
                    purchase_order_id=purchase_order.id,
                    occurred_at=effective_receipt_date,
                )
            )
            uow.commit()
        self._dispatch_procurement_financial_events()
        return receipt

    def apply_submitted_purchase_order_approval(
        self,
        request: ApprovalRequest,
    ) -> ApprovalHandlerResult:
        purchase_order = self._purchase_order_repo.get(request.entity_id)
        if purchase_order is None:
            raise NotFoundError("Purchase order not found.", code="INVENTORY_PURCHASE_ORDER_NOT_FOUND")
        if purchase_order.approval_request_id != request.id:
            raise ValidationError(
                "Approval request does not match the purchase order.",
                code="INVENTORY_PURCHASE_ORDER_APPROVAL_MISMATCH",
            )
        current_status = purchase_order.status.value
        if current_status not in {
            PurchaseOrderStatus.SUBMITTED.value,
            PurchaseOrderStatus.UNDER_REVIEW.value,
        }:
            raise ValidationError(
                "Purchase order is not awaiting approval.",
                code="INVENTORY_PURCHASE_ORDER_STATUS_INVALID",
            )
        validate_transition(
            current_status=current_status,
            next_status=PurchaseOrderStatus.APPROVED.value,
            transitions=PURCHASE_ORDER_STATUS_TRANSITIONS,
        )
        effective_at = datetime.now(timezone.utc)
        purchase_order = replace(
            purchase_order,
            status=PurchaseOrderStatus.APPROVED,
            approved_at=effective_at,
            updated_at=effective_at,
        )
        self._purchase_order_repo.update(purchase_order)
        lines = self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)
        touched_requisition_ids: set[str] = set()
        balance_events: list[StockOnOrderQuantityChanged] = []
        for line in lines:
            line = replace(line, status=PurchaseOrderLineStatus.OPEN)
            self._purchase_order_line_repo.update(line)
            previous_balance = self._balance_repo.get_for_stock_position(
                purchase_order.organization_id,
                line.stock_item_id,
                line.destination_storeroom_id,
            )
            previous_on_order = float(previous_balance.on_order_qty) if previous_balance else 0.0
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
                balance_events.append(
                    StockOnOrderQuantityChanged(
                        tenant_id=request.tenant_id,
                        organization_id=purchase_order.organization_id,
                        balance_id=balance.id,
                        stock_item_id=balance.stock_item_id,
                        storeroom_id=balance.storeroom_id,
                        quantity_delta=float(balance.on_order_qty) - previous_on_order,
                        resulting_quantity=balance.on_order_qty,
                        occurred_at=effective_at,
                    )
                )
            if line.source_requisition_line_id:
                requisition_line = self._require_requisition_line(line.source_requisition_line_id)
                requisition_for_line = self._requisition_repo.get(
                    requisition_line.purchase_requisition_id
                )
                if (
                    requisition_for_line is None
                    or requisition_for_line.organization_id != purchase_order.organization_id
                ):
                    raise ValidationError(
                        "Source requisition line does not belong to the purchase order's"
                        " organization.",
                        code="INVENTORY_REQUISITION_LINE_ORG_MISMATCH",
                    )
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
                requested_qty = float(requisition_line.quantity_requested or 0.0)
                if new_sourced_qty <= 0:
                    next_requisition_status = PurchaseRequisitionLineStatus.OPEN
                elif new_sourced_qty >= requested_qty:
                    next_requisition_status = PurchaseRequisitionLineStatus.FULLY_SOURCED
                else:
                    next_requisition_status = PurchaseRequisitionLineStatus.PARTIALLY_SOURCED
                requisition_line = replace(
                    requisition_line,
                    quantity_sourced=new_sourced_qty,
                    status=next_requisition_status,
                )
                self._requisition_line_repo.update(requisition_line)
                touched_requisition_ids.add(requisition_line.purchase_requisition_id)
        requisition_sourcing_events: list[InventoryRequisitionSourcingAdvanced] = []
        for requisition_id in sorted(touched_requisition_ids):
            requisition = self._requisition_repo.get(requisition_id)
            if requisition is None:
                continue
            requisition = self._refresh_requisition_status(requisition)
            requisition_sourcing_events.append(
                InventoryRequisitionSourcingAdvanced(
                    tenant_id=request.tenant_id,
                    organization_id=purchase_order.organization_id,
                    requisition_id=requisition.id,
                    purchase_order_id=purchase_order.id,
                    resulting_status=requisition.status.value,
                    occurred_at=effective_at,
                )
            )
        record_activity(
            self,
            action="inventory_purchase_order.approve",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            module="inventory",
            details={
                "po_number": purchase_order.po_number,
                "approval_request_id": request.id,
            },
            commit=False,
        )
        return ApprovalHandlerResult(
            domain_events=(
                InventoryPurchaseOrderApproved(
                    tenant_id=request.tenant_id,
                    organization_id=purchase_order.organization_id,
                    purchase_order_id=purchase_order.id,
                    approval_request_id=request.id,
                    occurred_at=effective_at,
                ),
                *requisition_sourcing_events,
                *balance_events,
            ),
        )

    def apply_submitted_purchase_order_rejection(
        self,
        request: ApprovalRequest,
    ) -> ApprovalHandlerResult:
        purchase_order = self._purchase_order_repo.get(request.entity_id)
        if purchase_order is None:
            raise NotFoundError("Purchase order not found.", code="INVENTORY_PURCHASE_ORDER_NOT_FOUND")
        if purchase_order.approval_request_id != request.id:
            raise ValidationError(
                "Approval request does not match the purchase order.",
                code="INVENTORY_PURCHASE_ORDER_APPROVAL_MISMATCH",
            )
        current_status = purchase_order.status.value
        if current_status not in {
            PurchaseOrderStatus.SUBMITTED.value,
            PurchaseOrderStatus.UNDER_REVIEW.value,
        }:
            raise ValidationError(
                "Purchase order is not awaiting approval.",
                code="INVENTORY_PURCHASE_ORDER_STATUS_INVALID",
            )
        validate_transition(
            current_status=current_status,
            next_status=PurchaseOrderStatus.REJECTED.value,
            transitions=PURCHASE_ORDER_STATUS_TRANSITIONS,
        )
        effective_at = datetime.now(timezone.utc)
        purchase_order = replace(
            purchase_order,
            status=PurchaseOrderStatus.REJECTED,
            updated_at=effective_at,
        )
        self._purchase_order_repo.update(purchase_order)
        for line in self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id):
            line = replace(line, status=PurchaseOrderLineStatus.CANCELLED)
            self._purchase_order_line_repo.update(line)
        record_activity(
            self,
            action="inventory_purchase_order.reject",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            module="inventory",
            details={
                "po_number": purchase_order.po_number,
                "approval_request_id": request.id,
            },
            commit=False,
        )
        return ApprovalHandlerResult(
            domain_events=(
                InventoryPurchaseOrderRejected(
                    tenant_id=request.tenant_id,
                    organization_id=purchase_order.organization_id,
                    purchase_order_id=purchase_order.id,
                    approval_request_id=request.id,
                    occurred_at=effective_at,
                ),
            )
        )


__all__ = ["PurchasingReceivingMixin"]
