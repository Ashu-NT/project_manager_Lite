from __future__ import annotations

from datetime import datetime, timezone

from core.modules.inventory_procurement.domain import PurchaseRequisitionLineStatus, PurchaseRequisitionStatus
from core.modules.inventory_procurement.support import REQUISITION_STATUS_TRANSITIONS, validate_transition
from src.core.platform.approval.domain import ApprovalRequest
from src.core.platform.audit.helpers import record_audit
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import domain_events


class ProcurementApprovalMixin:
    def apply_submitted_requisition_approval(self, request: ApprovalRequest) -> None:
        requisition = self._requisition_repo.get(request.entity_id)
        if requisition is None:
            raise NotFoundError("Purchase requisition not found.", code="INVENTORY_REQUISITION_NOT_FOUND")
        if requisition.approval_request_id != request.id:
            raise ValidationError("Approval request does not match the requisition.", code="INVENTORY_REQUISITION_APPROVAL_MISMATCH")
        current_status = requisition.status.value
        if current_status not in {
            PurchaseRequisitionStatus.SUBMITTED.value,
            PurchaseRequisitionStatus.UNDER_REVIEW.value,
        }:
            raise ValidationError("Purchase requisition is not awaiting approval.", code="INVENTORY_REQUISITION_STATUS_INVALID")
        validate_transition(
            current_status=current_status,
            next_status=PurchaseRequisitionStatus.APPROVED.value,
            transitions=REQUISITION_STATUS_TRANSITIONS,
        )
        requisition.status = PurchaseRequisitionStatus.APPROVED
        requisition.approved_at = datetime.now(timezone.utc)
        requisition.updated_at = requisition.approved_at
        self._requisition_repo.update(requisition)
        for line in self._requisition_line_repo.list_for_requisition(requisition.id):
            line.status = PurchaseRequisitionLineStatus.OPEN
            self._requisition_line_repo.update(line)
        record_audit(
            self,
            action="inventory_requisition.approve",
            entity_type="purchase_requisition",
            entity_id=requisition.id,
            details={
                "requisition_number": requisition.requisition_number,
                "approval_request_id": request.id,
            },
        )
        domain_events.inventory_requisitions_changed.emit(requisition.id)

    def apply_submitted_requisition_rejection(self, request: ApprovalRequest) -> None:
        requisition = self._requisition_repo.get(request.entity_id)
        if requisition is None:
            raise NotFoundError("Purchase requisition not found.", code="INVENTORY_REQUISITION_NOT_FOUND")
        if requisition.approval_request_id != request.id:
            raise ValidationError("Approval request does not match the requisition.", code="INVENTORY_REQUISITION_APPROVAL_MISMATCH")
        current_status = requisition.status.value
        if current_status not in {
            PurchaseRequisitionStatus.SUBMITTED.value,
            PurchaseRequisitionStatus.UNDER_REVIEW.value,
        }:
            raise ValidationError("Purchase requisition is not awaiting approval.", code="INVENTORY_REQUISITION_STATUS_INVALID")
        validate_transition(
            current_status=current_status,
            next_status=PurchaseRequisitionStatus.REJECTED.value,
            transitions=REQUISITION_STATUS_TRANSITIONS,
        )
        requisition.status = PurchaseRequisitionStatus.REJECTED
        requisition.updated_at = datetime.now(timezone.utc)
        self._requisition_repo.update(requisition)
        for line in self._requisition_line_repo.list_for_requisition(requisition.id):
            line.status = PurchaseRequisitionLineStatus.REJECTED
            self._requisition_line_repo.update(line)
        record_audit(
            self,
            action="inventory_requisition.reject",
            entity_type="purchase_requisition",
            entity_id=requisition.id,
            details={
                "requisition_number": requisition.requisition_number,
                "approval_request_id": request.id,
            },
        )
        domain_events.inventory_requisitions_changed.emit(requisition.id)


__all__ = ["ProcurementApprovalMixin"]
