from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError

from src.core.modules.inventory_procurement.application.common.support import (
    PURCHASE_ORDER_STATUS_TRANSITIONS,
    normalize_nonnegative_quantity,
    normalize_optional_text,
    normalize_positive_quantity,
    normalize_uom,
    resolve_item_uom_factor,
    validate_transition,
)
from src.core.modules.inventory_procurement.application.procurement.purchasing_support import (
    build_purchase_order_number,
    normalize_currency_code,
)
from src.core.modules.inventory_procurement.domain.inventory.balance_events import (
    StockOnOrderQuantityChanged,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderLineStatus,
    PurchaseOrderStatus,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing_events import (
    InventoryPurchaseOrderCancelled,
    InventoryPurchaseOrderClosed,
    InventoryPurchaseOrderCreated,
    InventoryPurchaseOrderLineAdded,
    InventoryPurchaseOrderProfileUpdated,
    InventoryPurchaseOrderSent,
    InventoryPurchaseOrderSubmitted,
)
from src.core.platform.application.approval.approval_mutation_participant import (
    request_approval_using,
)
from src.core.platform.common.ids import generate_id
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, ValidationError
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext


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
            raise ValidationError(
                "Selected site must be active in the current organization.",
                code="INVENTORY_SITE_SCOPE_INVALID",
            )
        supplier = self._reference_service.get_party(supplier_party_id)
        if supplier.organization_id != organization.id or not supplier.is_active:
            raise ValidationError(
                "Selected supplier must be active in the current organization.",
                code="INVENTORY_SUPPLIER_SCOPE_INVALID",
            )
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
            supplier_reference=supplier_reference,
            notes=notes,
        )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="create purchase order"
        )
        occurred_at = datetime.now(timezone.utc)
        try:
            with self._require_purchase_order_uow_factory().create(
                context=DomainEventContext(correlation_id=generate_id())
            ) as uow:
                uow.purchase_orders.add(purchase_order)
                record_activity(
                    uow,
                    action="inventory_purchase_order.create",
                    entity_type="purchase_order",
                    entity_id=purchase_order.id,
                    module="inventory",
                    details={
                        "po_number": purchase_order.po_number,
                        "site_id": purchase_order.site_id,
                        "supplier_party_id": purchase_order.supplier_party_id,
                        "source_requisition_id": purchase_order.source_requisition_id or "",
                    },
                    commit=False,
                )
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="purchase_order",
                    entity_id=purchase_order.id,
                    module="inventory",
                    severity="low",
                    metadata={
                        "po_number": purchase_order.po_number,
                        "site_id": purchase_order.site_id,
                        "supplier_party_id": purchase_order.supplier_party_id,
                    },
                    commit=False,
                    fail_closed=True,
                )
                uow.record_event(
                    InventoryPurchaseOrderCreated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        purchase_order_id=purchase_order.id,
                        occurred_at=occurred_at,
                    )
                )
                uow.commit()
        except IntegrityError as exc:
            raise ValidationError(
                "Purchase order number already exists.",
                code="INVENTORY_PURCHASE_ORDER_NUMBER_EXISTS",
            ) from exc
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
            raise ValidationError(
                "Purchase-order item must be active in the current organization.",
                code="INVENTORY_PO_ITEM_SCOPE_INVALID",
            )
        if not item.is_purchase_allowed:
            raise ValidationError(
                "Purchase-order item is not enabled for purchasing.",
                code="INVENTORY_ITEM_PURCHASE_FORBIDDEN",
            )
        storeroom = self._inventory_service.get_storeroom(destination_storeroom_id)
        if storeroom.organization_id != purchase_order.organization_id or not storeroom.is_active:
            raise ValidationError(
                "Destination storeroom must be active in the current organization.",
                code="INVENTORY_PO_STOREROOM_SCOPE_INVALID",
            )
        if storeroom.site_id != purchase_order.site_id:
            raise ValidationError(
                "Destination storeroom must belong to the purchase-order site.",
                code="INVENTORY_PO_SITE_STOREROOM_MISMATCH",
            )
        if not storeroom.allows_receiving:
            raise ValidationError(
                "Destination storeroom does not allow receiving.",
                code="INVENTORY_RECEIVING_FORBIDDEN",
            )
        next_line_number = len(self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)) + 1
        line = PurchaseOrderLine.create(
            purchase_order_id=purchase_order.id,
            line_number=next_line_number,
            stock_item_id=item.id,
            destination_storeroom_id=storeroom.id,
            description=description or item.name,
            quantity_ordered=quantity_ordered,
            uom=uom or item.stock_uom,
            unit_price=unit_price,
            expected_delivery_date=expected_delivery_date,
            source_requisition_line_id=source_requisition_line_id,
            notes=notes,
        )
        resolve_item_uom_factor(item, line.uom, label="Purchase-order line UOM")
        source_line = self._validate_source_requisition_line(
            purchase_order=purchase_order,
            item=item,
            source_requisition_line_id=line.source_requisition_line_id,
            quantity_ordered=line.quantity_ordered,
            quantity_ordered_uom=line.uom,
        )
        if source_line is not None and line.source_requisition_line_id != source_line.id:
            line = replace(line, source_requisition_line_id=source_line.id)
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="add purchase order line"
        )
        occurred_at = datetime.now(timezone.utc)
        try:
            with self._require_purchase_order_uow_factory().create(
                context=DomainEventContext(correlation_id=generate_id())
            ) as uow:
                uow.purchase_order_lines.add(line)
                record_activity(
                    uow,
                    action="inventory_purchase_order_line.create",
                    entity_type="purchase_order_line",
                    entity_id=line.id,
                    module="inventory",
                    details={
                        "purchase_order_id": purchase_order.id,
                        "line_number": str(line.line_number),
                        "stock_item_id": line.stock_item_id,
                        "destination_storeroom_id": line.destination_storeroom_id,
                        "source_requisition_line_id": line.source_requisition_line_id or "",
                    },
                    commit=False,
                )
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="purchase_order_line",
                    entity_id=line.id,
                    module="inventory",
                    severity="low",
                    metadata={
                        "purchase_order_id": purchase_order.id,
                        "line_number": str(line.line_number),
                        "stock_item_id": line.stock_item_id,
                    },
                    commit=False,
                    fail_closed=True,
                )
                uow.record_event(
                    InventoryPurchaseOrderLineAdded(
                        tenant_id=tenant_id,
                        organization_id=purchase_order.organization_id,
                        purchase_order_id=purchase_order.id,
                        purchase_order_line_id=line.id,
                        occurred_at=occurred_at,
                    )
                )
                uow.commit()
        except IntegrityError as exc:
            raise ValidationError(
                "Purchase order line already exists.",
                code="INVENTORY_PURCHASE_ORDER_LINE_EXISTS",
            ) from exc
        return line

    def submit_purchase_order(self, purchase_order_id: str, *, note: str = "") -> PurchaseOrder:
        """Approval-P1: converged onto `PurchaseOrderSubmissionUnitOfWork` -- one fresh Session,
        one transaction, for the purchase order transition, the Approval-request participant,
        and the Approval audit entry together. The pre-mutation reads below (`_require_draft_
        purchase_order`/`list_for_purchase_order`/reference lookups) intentionally stay on the
        shared, process-lifetime Session -- they only inform what the transaction below will
        write; `validate_transition` still fails a genuinely stale status regardless of which
        Session performed the read."""
        if self._purchase_order_submission_uow_factory is None:
            raise BusinessRuleError(
                "Purchase order submission requires a configured transaction owner.",
                code="INVENTORY_PURCHASE_ORDER_SUBMISSION_UOW_REQUIRED",
            )
        if self._clock is None:
            raise BusinessRuleError(
                "Purchase order submission requires a configured Clock.",
                code="INVENTORY_PURCHASE_ORDER_CLOCK_REQUIRED",
            )
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
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="submit purchase order"
        )
        principal = self._user_session.principal if self._user_session is not None else None
        validate_transition(
            current_status=purchase_order.status.value,
            next_status=PurchaseOrderStatus.SUBMITTED.value,
            transitions=PURCHASE_ORDER_STATUS_TRANSITIONS,
        )
        effective_at = datetime.now(timezone.utc)

        with self._purchase_order_submission_uow_factory.create(
            context=DomainEventContext(correlation_id=generate_id())
        ) as uow:
            request = request_approval_using(
                approval_repo=uow.approvals,
                enterprise_audit_service=uow._enterprise_audit_service,
                clock=self._clock,
                record_event=uow.record_event,
                request_type="purchase_order.submit",
                entity_type="purchase_order",
                entity_id=purchase_order.id,
                tenant_id=tenant_id,
                organization_id=purchase_order.organization_id,
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
                    "expected_delivery_date": purchase_order.expected_delivery_date.isoformat()
                    if purchase_order.expected_delivery_date
                    else "",
                },
                requested_by_user_id=getattr(principal, "user_id", None),
                requested_by_username=str(getattr(principal, "username", "") or ""),
            )
            submitted_purchase_order = replace(
                purchase_order,
                status=PurchaseOrderStatus.SUBMITTED,
                approval_request_id=request.id,
                submitted_at=effective_at,
                updated_at=effective_at,
            )
            uow.purchase_orders.update(submitted_purchase_order)
            record_activity(
                uow,
                action="inventory_purchase_order.submit",
                entity_type="purchase_order",
                entity_id=submitted_purchase_order.id,
                module="inventory",
                details={
                    "po_number": submitted_purchase_order.po_number,
                    "approval_request_id": request.id,
                    "note": normalize_optional_text(note),
                },
                commit=False,
            )
            uow.record_event(
                InventoryPurchaseOrderSubmitted(
                    tenant_id=tenant_id,
                    organization_id=submitted_purchase_order.organization_id,
                    purchase_order_id=submitted_purchase_order.id,
                    approval_request_id=request.id,
                    occurred_at=effective_at,
                )
            )
            uow.commit()
        self._approval_service.publish_requested(request)
        return submitted_purchase_order

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
        candidate = replace(
            purchase_order,
            site_id=site.id,
            supplier_party_id=supplier.id,
            currency_code=normalize_currency_code(
                currency_code,
                fallback=getattr(site, "currency_code", ""),
            ),
            source_requisition_id=requisition.id if requisition is not None else None,
            expected_delivery_date=expected_delivery_date,
            supplier_reference=(
                purchase_order.supplier_reference
                if supplier_reference is None
                else supplier_reference
            ),
            notes=purchase_order.notes if notes is None else notes,
        )
        if candidate == purchase_order:
            # True no-op (P28B SS20): zero repository write, zero audit, zero typed event, no
            # synthetic version/updated_at bump.
            return purchase_order
        now = datetime.now(timezone.utc)
        candidate = replace(candidate, updated_at=now)
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="update purchase order"
        )
        with self._require_purchase_order_uow_factory().create(
            context=DomainEventContext(correlation_id=generate_id())
        ) as uow:
            uow.purchase_orders.update(candidate)
            record_activity(
                uow,
                action="inventory_purchase_order.update",
                entity_type="purchase_order",
                entity_id=candidate.id,
                module="inventory",
                details={
                    "po_number": candidate.po_number,
                    "site_id": candidate.site_id,
                    "supplier_party_id": candidate.supplier_party_id,
                    "source_requisition_id": candidate.source_requisition_id or "",
                },
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="purchase_order",
                entity_id=candidate.id,
                module="inventory",
                severity="low",
                metadata={
                    "po_number": candidate.po_number,
                    "site_id": candidate.site_id,
                    "supplier_party_id": candidate.supplier_party_id,
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                InventoryPurchaseOrderProfileUpdated(
                    tenant_id=tenant_id,
                    organization_id=candidate.organization_id,
                    purchase_order_id=candidate.id,
                    occurred_at=now,
                )
            )
            uow.commit()
        return candidate

    def cancel_purchase_order(
        self,
        purchase_order_id: str,
        *,
        note: str = "",
        expected_version: int | None = None,
    ) -> PurchaseOrder:
        self._require_manage("cancel purchase order")
        purchase_order = self.get_purchase_order(purchase_order_id)
        if purchase_order.status not in {
            PurchaseOrderStatus.DRAFT,
            PurchaseOrderStatus.APPROVED,
            PurchaseOrderStatus.SENT,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
        }:
            raise ValidationError(
                "Purchase order cannot be cancelled from its current status.",
                code="INVENTORY_PURCHASE_ORDER_CANCEL_STATUS_INVALID",
            )
        if (
            purchase_order.status != PurchaseOrderStatus.DRAFT
            and not normalize_optional_text(note)
        ):
            raise ValidationError(
                "A cancellation reason is required after purchase-order approval.",
                code="INVENTORY_PURCHASE_ORDER_CANCEL_REASON_REQUIRED",
            )
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
        prior_status = purchase_order.status
        effective_at = datetime.now(timezone.utc)
        cancelled_purchase_order = replace(
            purchase_order,
            status=PurchaseOrderStatus.CANCELLED,
            cancelled_at=effective_at,
            updated_at=effective_at,
        )
        lines = self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="cancel purchase order"
        )
        with self._require_purchase_order_uow_factory().create(
            context=DomainEventContext(correlation_id=generate_id())
        ) as uow:
            for line in lines:
                outstanding = self._line_outstanding_qty(line)
                if outstanding > 0 and prior_status != PurchaseOrderStatus.DRAFT:
                    # P31B: fixes the confirmed silent-mutation gap (P31A) -- this on-order
                    # reversal previously emitted no Balance notification of any kind.
                    previous_balance = uow.balances.get_for_stock_position(
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
                        delta=-outstanding,
                        effective_at=effective_at,
                        balance_repo=uow.balances,
                    )
                    balance = uow.balances.get_for_stock_position(
                        purchase_order.organization_id,
                        line.stock_item_id,
                        line.destination_storeroom_id,
                    )
                    if balance is not None:
                        uow.record_event(
                            StockOnOrderQuantityChanged(
                                tenant_id=tenant_id,
                                organization_id=purchase_order.organization_id,
                                balance_id=balance.id,
                                stock_item_id=balance.stock_item_id,
                                storeroom_id=balance.storeroom_id,
                                quantity_delta=float(balance.on_order_qty) - previous_on_order,
                                resulting_quantity=balance.on_order_qty,
                                occurred_at=effective_at,
                            )
                        )
                line = replace(line, status=PurchaseOrderLineStatus.CANCELLED)
                uow.purchase_order_lines.update(line)
            uow.purchase_orders.update(cancelled_purchase_order)
            self._enqueue_purchase_order_financial_events(cancelled_purchase_order, lines)
            record_activity(
                uow,
                action="inventory_purchase_order.cancel",
                entity_type="purchase_order",
                entity_id=cancelled_purchase_order.id,
                module="inventory",
                details={
                    "po_number": cancelled_purchase_order.po_number,
                    "note": normalize_optional_text(note),
                },
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="purchase_order",
                entity_id=cancelled_purchase_order.id,
                module="inventory",
                severity="medium",
                metadata={
                    "po_number": cancelled_purchase_order.po_number,
                    "action": "cancel",
                    "note": normalize_optional_text(note),
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                InventoryPurchaseOrderCancelled(
                    tenant_id=tenant_id,
                    organization_id=cancelled_purchase_order.organization_id,
                    purchase_order_id=cancelled_purchase_order.id,
                    occurred_at=effective_at,
                )
            )
            uow.commit()
        self._dispatch_procurement_financial_events()
        return cancelled_purchase_order

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
        sent_purchase_order = replace(
            purchase_order,
            status=PurchaseOrderStatus.SENT,
            sent_at=effective_at,
            order_date=(
                purchase_order.order_date
                or purchase_order.expected_delivery_date
                or effective_at.date()
            ),
            updated_at=effective_at,
        )
        lines = self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="send purchase order"
        )
        with self._require_purchase_order_uow_factory().create(
            context=DomainEventContext(correlation_id=generate_id())
        ) as uow:
            uow.purchase_orders.update(sent_purchase_order)
            self._enqueue_purchase_order_financial_events(sent_purchase_order, lines)
            record_activity(
                uow,
                action="inventory_purchase_order.send",
                entity_type="purchase_order",
                entity_id=sent_purchase_order.id,
                module="inventory",
                details={
                    "po_number": sent_purchase_order.po_number,
                    "note": normalize_optional_text(note),
                },
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="purchase_order",
                entity_id=sent_purchase_order.id,
                module="inventory",
                severity="low",
                metadata={"po_number": sent_purchase_order.po_number, "action": "send"},
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                InventoryPurchaseOrderSent(
                    tenant_id=tenant_id,
                    organization_id=sent_purchase_order.organization_id,
                    purchase_order_id=sent_purchase_order.id,
                    occurred_at=effective_at,
                )
            )
            uow.commit()
        self._dispatch_procurement_financial_events()
        return sent_purchase_order

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
        closed_purchase_order = replace(
            purchase_order,
            status=PurchaseOrderStatus.CLOSED,
            closed_at=effective_at,
            updated_at=effective_at,
        )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="close purchase order"
        )
        with self._require_purchase_order_uow_factory().create(
            context=DomainEventContext(correlation_id=generate_id())
        ) as uow:
            uow.purchase_orders.update(closed_purchase_order)
            self._enqueue_purchase_order_financial_events(closed_purchase_order, lines)
            record_activity(
                uow,
                action="inventory_purchase_order.close",
                entity_type="purchase_order",
                entity_id=closed_purchase_order.id,
                module="inventory",
                details={
                    "po_number": closed_purchase_order.po_number,
                    "note": normalize_optional_text(note),
                },
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="purchase_order",
                entity_id=closed_purchase_order.id,
                module="inventory",
                severity="low",
                metadata={"po_number": closed_purchase_order.po_number, "action": "close"},
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                InventoryPurchaseOrderClosed(
                    tenant_id=tenant_id,
                    organization_id=closed_purchase_order.organization_id,
                    purchase_order_id=closed_purchase_order.id,
                    occurred_at=effective_at,
                )
            )
            uow.commit()
        self._dispatch_procurement_financial_events()
        return closed_purchase_order


__all__ = ["PurchasingLifecycleMixin"]
