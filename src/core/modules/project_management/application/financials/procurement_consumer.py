from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.commitments import (
    ProjectCommitmentService,
)
from src.core.modules.project_management.application.financials.cost_entries import (
    ProjectCostEntryService,
)
from src.core.modules.project_management.contracts.financial_sources import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceReference,
    FinancialSourceType,
    ProcurementCommitmentFinancialSource,
    ProcurementCommitmentState,
    ProcurementReceiptAccrualFinancialSource,
)
from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.integration import (
    PROCUREMENT_COMMITMENT_EVENT_TYPE,
    PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE,
    IntegrationEventEnvelope,
    ProcurementCommitmentEventPayload,
    ProcurementReceiptAccrualEventPayload,
)


@dataclass(frozen=True)
class ProcurementFinancialConsumption:
    project_id: str
    commitment_changed: bool = False
    cost_entry_changed: bool = False


class ProcurementFinancialConsumer:
    def __init__(
        self,
        *,
        commitment_service: ProjectCommitmentService,
        cost_entry_service: ProjectCostEntryService,
        task_repo: TaskRepository,
    ) -> None:
        self._commitment_service = commitment_service
        self._cost_entry_service = cost_entry_service
        self._task_repo = task_repo

    def consume(
        self, envelope: IntegrationEventEnvelope
    ) -> ProcurementFinancialConsumption:
        if envelope.event_type == PROCUREMENT_COMMITMENT_EVENT_TYPE:
            return self._consume_commitment(envelope)
        if envelope.event_type == PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE:
            return self._consume_receipt(envelope)
        raise BusinessRuleError(
            "Unsupported Procurement financial event.",
            code="PROCUREMENT_FINANCIAL_EVENT_UNSUPPORTED",
        )

    def _consume_commitment(
        self, envelope: IntegrationEventEnvelope
    ) -> ProcurementFinancialConsumption:
        payload = ProcurementCommitmentEventPayload.model_validate(envelope.payload)
        project_id, task_id = self._resolve_project(payload.project_id, payload.task_id)
        reference = FinancialSourceReference(
            tenant_id=envelope.tenant_id,
            organization_id=str(envelope.organization_id),
            project_id=project_id,
            source_module=FinancialSourceModule.INVENTORY_PROCUREMENT,
            source_type=FinancialSourceType.PURCHASE_ORDER_LINE,
            source_id=payload.purchase_order_id,
            source_line_id=payload.purchase_order_line_id,
            source_revision=str(payload.source_revision),
            content_hash=payload.source_content_hash,
            posting_purpose=FinancialPostingPurpose.PURCHASE_COMMITMENT,
        )
        source = ProcurementCommitmentFinancialSource(
            reference=reference,
            purchase_order_id=payload.purchase_order_id,
            purchase_order_line_id=payload.purchase_order_line_id,
            purchase_order_number=payload.purchase_order_number,
            supplier_party_id=payload.supplier_party_id,
            site_id=payload.site_id,
            state=ProcurementCommitmentState(payload.state),
            ordered_quantity=payload.ordered_quantity,
            unit_price=payload.unit_price,
            order_date=payload.order_date,
            expected_delivery_date=payload.expected_delivery_date,
            source_requisition_id=payload.source_requisition_id,
            source_requisition_line_id=payload.source_requisition_line_id,
            task_id=task_id,
        )
        self._commitment_service.apply_procurement_source(source)
        return ProcurementFinancialConsumption(
            project_id=project_id, commitment_changed=True
        )

    def _consume_receipt(
        self, envelope: IntegrationEventEnvelope
    ) -> ProcurementFinancialConsumption:
        payload = ProcurementReceiptAccrualEventPayload.model_validate(envelope.payload)
        project_id, task_id = self._resolve_project(payload.project_id, payload.task_id)
        reference = FinancialSourceReference(
            tenant_id=envelope.tenant_id,
            organization_id=str(envelope.organization_id),
            project_id=project_id,
            source_module=FinancialSourceModule.INVENTORY_PROCUREMENT,
            source_type=FinancialSourceType.RECEIPT_LINE,
            source_id=payload.receipt_id,
            source_line_id=payload.receipt_line_id,
            source_revision=str(payload.source_revision),
            content_hash=payload.source_content_hash,
            posting_purpose=FinancialPostingPurpose.RECEIPT_ACCRUAL,
        )
        source = ProcurementReceiptAccrualFinancialSource(
            reference=reference,
            receipt_id=payload.receipt_id,
            receipt_line_id=payload.receipt_line_id,
            receipt_number=payload.receipt_number,
            purchase_order_id=payload.purchase_order_id,
            purchase_order_line_id=payload.purchase_order_line_id,
            supplier_party_id=payload.supplier_party_id,
            site_id=payload.site_id,
            posted_at=payload.posted_at,
            accepted_quantity=payload.accepted_quantity,
            unit_cost=payload.unit_cost,
            task_id=task_id,
        )
        entry = self._cost_entry_service.apply_procurement_receipt_source(source)
        self._commitment_service.apply_procurement_receipt_match(
            purchase_order_id=payload.purchase_order_id,
            purchase_order_line_id=payload.purchase_order_line_id,
            cost_entry_id=entry.id,
            supplier_party_id=payload.supplier_party_id,
            site_id=payload.site_id,
        )
        return ProcurementFinancialConsumption(
            project_id=project_id,
            commitment_changed=True,
            cost_entry_changed=True,
        )

    def _resolve_project(
        self, project_id: str | None, task_id: str | None
    ) -> tuple[str, str | None]:
        if task_id:
            task = self._task_repo.get(task_id)
            if task is None:
                raise NotFoundError(
                    "Procurement source task not found.",
                    code="PROCUREMENT_FINANCIAL_TASK_NOT_FOUND",
                )
            if project_id and task.project_id != project_id:
                raise BusinessRuleError(
                    "Procurement project and task references disagree.",
                    code="PROCUREMENT_FINANCIAL_PROJECT_TASK_MISMATCH",
                )
            return task.project_id, task.id
        if project_id:
            return project_id, None
        raise BusinessRuleError(
            "Procurement financial event has no project context.",
            code="PROCUREMENT_FINANCIAL_PROJECT_REQUIRED",
        )


__all__ = ["ProcurementFinancialConsumer", "ProcurementFinancialConsumption"]
