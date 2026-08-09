from __future__ import annotations

import logging

from src.core.platform.common.ids import generate_id
from src.core.platform.finance import (
    DecimalQuantity,
    DecimalQuantityPayload,
    MonetaryRate,
    MonetaryRatePayload,
    Money,
)
from src.core.platform.integration import (
    PROCUREMENT_COMMITMENT_EVENT_TYPE,
    PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE,
    IntegrationEventEnvelope,
    ProcurementCommitmentEventPayload,
    ProcurementReceiptAccrualEventPayload,
)
from src.core.platform.integration.canonical_json import canonical_json_sha256


logger = logging.getLogger(__name__)


class PurchasingFinancialEventsMixin:
    def _project_financial_source(self, purchase_order):
        if not purchase_order.source_requisition_id:
            return None
        requisition = self._requisition_repo.get(purchase_order.source_requisition_id)
        if requisition is None or requisition.source_module != "project_management":
            return None
        reference_type = str(requisition.source_reference_type or "").lower()
        if reference_type == "project":
            return requisition.source_reference_id, None
        if reference_type == "task":
            return None, requisition.source_reference_id
        return None

    def _enqueue_purchase_order_financial_events(self, purchase_order, lines) -> int:
        outbox = getattr(self, "_procurement_financial_outbox_service", None)
        source = self._project_financial_source(purchase_order)
        if outbox is None or source is None:
            return 0
        project_id, task_id = source
        state = purchase_order.status.value
        if state not in {
            "SENT", "PARTIALLY_RECEIVED", "FULLY_RECEIVED", "CLOSED", "CANCELLED"
        }:
            return 0
        context = self._tenant_context_service.require_active_scope_ids(
            operation_label="publish purchase order financial state"
        )
        occurred_at = purchase_order.updated_at or purchase_order.sent_at
        emitted = 0
        for line in lines:
            latest = outbox.latest_for_aggregate(
                aggregate_type="purchase_order_line", aggregate_id=line.id
            )
            if latest is None and state in {"CLOSED", "CANCELLED"}:
                continue
            revision = latest.envelope.aggregate_version + 1 if latest is not None else 1
            facts = {
                "purchase_order_id": purchase_order.id,
                "purchase_order_line_id": line.id,
                "purchase_order_number": purchase_order.po_number,
                "supplier_party_id": purchase_order.supplier_party_id,
                "site_id": purchase_order.site_id,
                "state": state,
                "project_id": project_id,
                "task_id": task_id,
                "source_module": "project_management",
                "ordered_quantity": DecimalQuantityPayload.from_domain(
                    DecimalQuantity.of(str(line.quantity_ordered), line.uom)
                ).model_dump(mode="json"),
                "unit_price": MonetaryRatePayload.from_domain(
                    MonetaryRate(
                        Money.of(str(line.unit_price), purchase_order.currency_code),
                        line.uom,
                    )
                ).model_dump(mode="json"),
                "order_date": purchase_order.order_date.isoformat() if purchase_order.order_date else None,
                "expected_delivery_date": (
                    line.expected_delivery_date or purchase_order.expected_delivery_date
                ).isoformat() if (line.expected_delivery_date or purchase_order.expected_delivery_date) else None,
                "source_requisition_id": purchase_order.source_requisition_id,
                "source_requisition_line_id": line.source_requisition_line_id,
            }
            content_hash = canonical_json_sha256(facts)
            if latest is not None:
                prior = ProcurementCommitmentEventPayload.model_validate(
                    latest.envelope.payload
                )
                if prior.source_content_hash == content_hash:
                    continue
            payload = ProcurementCommitmentEventPayload(
                **facts,
                source_revision=revision,
                source_content_hash=content_hash,
            )
            outbox.enqueue(IntegrationEventEnvelope(
                event_id=generate_id(),
                event_type=PROCUREMENT_COMMITMENT_EVENT_TYPE,
                schema_version=1,
                tenant_id=context.tenant_id,
                organization_id=context.organization_id,
                aggregate_type="purchase_order_line",
                aggregate_id=line.id,
                aggregate_version=revision,
                occurred_at=occurred_at,
                correlation_id=purchase_order.id,
                payload=payload.model_dump(mode="json"),
            ))
            emitted += 1
        return emitted

    def _enqueue_receipt_financial_events(
        self, *, purchase_order, receipt, receipt_lines
    ) -> int:
        outbox = getattr(self, "_procurement_financial_outbox_service", None)
        source = self._project_financial_source(purchase_order)
        if outbox is None or source is None:
            return 0
        project_id, task_id = source
        context = self._tenant_context_service.require_active_scope_ids(
            operation_label="publish receipt financial accrual"
        )
        emitted = 0
        for line in receipt_lines:
            if line.quantity_accepted <= 0:
                continue
            facts = {
                "receipt_id": receipt.id,
                "receipt_line_id": line.id,
                "receipt_number": receipt.receipt_number,
                "purchase_order_id": purchase_order.id,
                "purchase_order_line_id": line.purchase_order_line_id,
                "supplier_party_id": receipt.supplier_party_id,
                "site_id": receipt.received_site_id,
                "project_id": project_id,
                "task_id": task_id,
                "source_module": "project_management",
                "posted_at": receipt.receipt_date.isoformat(),
                "accepted_quantity": DecimalQuantityPayload.from_domain(
                    DecimalQuantity.of(str(line.quantity_accepted), line.uom)
                ).model_dump(mode="json"),
                "unit_cost": MonetaryRatePayload.from_domain(
                    MonetaryRate(
                        Money.of(str(line.unit_cost), purchase_order.currency_code),
                        line.uom,
                    )
                ).model_dump(mode="json"),
            }
            content_hash = canonical_json_sha256(facts)
            payload = ProcurementReceiptAccrualEventPayload(
                **facts, source_revision=1, source_content_hash=content_hash
            )
            outbox.enqueue(IntegrationEventEnvelope(
                event_id=generate_id(),
                event_type=PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE,
                schema_version=1,
                tenant_id=context.tenant_id,
                organization_id=context.organization_id,
                aggregate_type="receipt_line",
                aggregate_id=line.id,
                aggregate_version=1,
                occurred_at=receipt.receipt_date,
                correlation_id=receipt.id,
                causation_id=purchase_order.id,
                payload=payload.model_dump(mode="json"),
            ))
            emitted += 1
        return emitted

    def _dispatch_procurement_financial_events(self) -> None:
        dispatcher = getattr(self, "_procurement_financial_dispatcher", None)
        if dispatcher is None:
            return
        try:
            dispatcher(limit=50)
        except Exception:
            logger.exception(
                "Procurement financial dispatch failed; durable events remain pending"
            )


__all__ = ["PurchasingFinancialEventsMixin"]
