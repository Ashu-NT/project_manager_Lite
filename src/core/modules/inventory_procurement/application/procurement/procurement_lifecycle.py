from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError

from src.core.modules.inventory_procurement.application.common.support import (
    REQUISITION_STATUS_TRANSITIONS,
    normalize_nonnegative_quantity,
    normalize_optional_date,
    normalize_optional_text,
    normalize_positive_quantity,
    normalize_source_reference_type,
    normalize_uom,
    resolve_item_uom_factor,
    validate_transition,
)
from src.core.modules.inventory_procurement.application.procurement.procurement_support import (
    build_requisition_number,
    normalize_priority,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseRequisition,
    PurchaseRequisitionLine,
    PurchaseRequisitionLineStatus,
    PurchaseRequisitionStatus,
)
from src.core.platform.application.approval.approval_mutation_participant import (
    request_approval_using,
)
from src.core.platform.common.ids import generate_id
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.common.exceptions import ConcurrencyError, ValidationError
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events


class ProcurementLifecycleMixin:
    def create_requisition(
        self,
        *,
        requesting_site_id: str,
        requesting_storeroom_id: str,
        purpose: str = "",
        needed_by_date: date | None = None,
        priority: str = "NORMAL",
        source_reference_type: str = "",
        source_reference_id: str = "",
        source_module: str = "",
        source_entity_type: str = "",
        source_code_snapshot: str = "",
        source_title_snapshot: str = "",
        source_status_snapshot: str = "",
        notes: str = "",
        requisition_number: str | None = None,
    ) -> PurchaseRequisition:
        self._require_manage("create purchase requisition")
        organization = self._active_organization()
        storeroom = self._inventory_service.get_storeroom(requesting_storeroom_id)
        if not storeroom.is_active:
            raise ValidationError(
                "Requesting storeroom must be active.",
                code="INVENTORY_REQUISITION_STOREROOM_INACTIVE",
            )
        if storeroom.site_id != requesting_site_id:
            raise ValidationError(
                "Requesting storeroom must belong to the selected site.",
                code="INVENTORY_REQUISITION_SITE_STOREROOM_MISMATCH",
            )
        if storeroom.organization_id != organization.id:
            raise ValidationError(
                "Requesting storeroom must belong to the active organization.",
                code="INVENTORY_REQUISITION_STOREROOM_SCOPE_INVALID",
            )
        principal = self._user_session.principal if self._user_session is not None else None
        requisition = PurchaseRequisition.create(
            organization_id=organization.id,
            requisition_number=normalize_optional_text(requisition_number) or build_requisition_number(),
            requesting_site_id=requesting_site_id,
            requesting_storeroom_id=requesting_storeroom_id,
            requester_user_id=getattr(principal, "user_id", None),
            requester_username=str(getattr(principal, "username", "") or ""),
            purpose=purpose,
            needed_by_date=needed_by_date,
            priority=priority,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            source_module=source_module,
            source_entity_type=source_entity_type,
            source_code_snapshot=source_code_snapshot,
            source_title_snapshot=source_title_snapshot,
            source_status_snapshot=source_status_snapshot,
            notes=notes,
        )
        try:
            self._requisition_repo.add(requisition)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Requisition number already exists.",
                code="INVENTORY_REQUISITION_NUMBER_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_activity(
            self,
            action="inventory_requisition.create",
            entity_type="purchase_requisition",
            entity_id=requisition.id,
            module="inventory",
            details={
                "requisition_number": requisition.requisition_number,
                "site_id": requisition.requesting_site_id,
                "storeroom_id": requisition.requesting_storeroom_id,
                "priority": requisition.priority,
            },
        )
        domain_events.inventory_requisitions_changed.emit(requisition.id)
        return requisition

    def add_requisition_line(
        self,
        requisition_id: str,
        *,
        stock_item_id: str,
        quantity_requested: float,
        uom: str | None = None,
        description: str = "",
        needed_by_date: date | None = None,
        estimated_unit_cost: float = 0.0,
        suggested_supplier_party_id: str | None = None,
        notes: str = "",
    ) -> PurchaseRequisitionLine:
        self._require_manage("add purchase requisition line")
        requisition = self._require_draft_requisition(requisition_id)
        item = self._item_service.get_item(stock_item_id)
        if item.organization_id != requisition.organization_id:
            raise ValidationError(
                "Requisition line item must belong to the active organization.",
                code="INVENTORY_REQUISITION_ITEM_SCOPE_INVALID",
            )
        if not item.is_active:
            raise ValidationError("Requisition line item must be active.", code="INVENTORY_ITEM_INACTIVE")
        if not item.is_purchase_allowed:
            raise ValidationError(
                "Requisition line item is not allowed for purchasing.",
                code="INVENTORY_ITEM_PURCHASE_FORBIDDEN",
            )
        supplier_id = self._validate_supplier_reference(suggested_supplier_party_id)
        next_line_number = len(self._requisition_line_repo.list_for_requisition(requisition.id)) + 1
        line = PurchaseRequisitionLine.create(
            purchase_requisition_id=requisition.id,
            line_number=next_line_number,
            stock_item_id=item.id,
            description=description or item.name,
            quantity_requested=quantity_requested,
            uom=uom or item.stock_uom,
            needed_by_date=needed_by_date,
            estimated_unit_cost=estimated_unit_cost,
            suggested_supplier_party_id=supplier_id,
            status=PurchaseRequisitionLineStatus.DRAFT,
            notes=notes,
        )
        resolve_item_uom_factor(item, line.uom, label="Requisition line UOM")
        try:
            self._requisition_line_repo.add(line)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Requisition line already exists.",
                code="INVENTORY_REQUISITION_LINE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_activity(
            self,
            action="inventory_requisition_line.create",
            entity_type="purchase_requisition_line",
            entity_id=line.id,
            module="inventory",
            details={
                "requisition_id": requisition.id,
                "line_number": str(line.line_number),
                "stock_item_id": line.stock_item_id,
                "quantity_requested": str(line.quantity_requested),
                "uom": line.uom,
            },
        )
        domain_events.inventory_requisitions_changed.emit(requisition.id)
        return line

    def submit_requisition(self, requisition_id: str, *, note: str = "") -> PurchaseRequisition:
        """Approval-P1: converged onto `RequisitionSubmissionUnitOfWork` -- one fresh Session,
        one transaction, for the requisition transition, the Approval-request participant, and
        the Approval audit entry together. The pre-mutation reads below (`_require_draft_
        requisition`/`list_for_requisition`) intentionally stay on the shared, process-lifetime
        Session -- they only inform what the transaction below will write; `update_with_version_
        check` still fails a genuinely stale write regardless of which Session performed the
        read."""
        self._require_manage("submit purchase requisition")
        requisition = self._require_draft_requisition(requisition_id)
        lines = self._requisition_line_repo.list_for_requisition(requisition.id)
        if not lines:
            raise ValidationError(
                "Purchase requisition must have at least one line before submission.",
                code="INVENTORY_REQUISITION_LINES_REQUIRED",
            )
        validate_transition(
            current_status=requisition.status.value,
            next_status=PurchaseRequisitionStatus.SUBMITTED.value,
            transitions=REQUISITION_STATUS_TRANSITIONS,
        )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="submit purchase requisition"
        )
        organization = self._active_organization()
        payload = {
            "requisition_id": requisition.id,
            "requisition_number": requisition.requisition_number,
            "site_id": requisition.requesting_site_id,
            "storeroom_id": requisition.requesting_storeroom_id,
            "purpose": requisition.purpose,
            "line_count": len(lines),
        }
        effective_at = datetime.now(timezone.utc)
        submitted_lines = [replace(line, status=PurchaseRequisitionLineStatus.DRAFT) for line in lines]
        principal = self._user_session.principal if self._user_session is not None else None

        with self._requisition_submission_uow_factory.create(
            context=DomainEventContext(correlation_id=generate_id())
        ) as uow:
            request = request_approval_using(
                approval_repo=uow.approvals,
                enterprise_audit_service=uow._enterprise_audit_service,
                request_type="purchase_requisition.submit",
                entity_type="purchase_requisition",
                entity_id=requisition.id,
                tenant_id=tenant_id,
                organization_id=organization.id,
                project_id=None,
                payload=payload,
                requested_by_user_id=getattr(principal, "user_id", None),
                requested_by_username=str(getattr(principal, "username", "") or ""),
            )
            submitted_requisition = replace(
                requisition,
                status=PurchaseRequisitionStatus.SUBMITTED,
                approval_request_id=request.id,
                submitted_at=effective_at,
                updated_at=effective_at,
            )
            for line in submitted_lines:
                uow.requisition_lines.update(line)
            uow.requisitions.update(submitted_requisition)
            uow.commit()
        record_activity(
            self,
            action="inventory_requisition.submit",
            entity_type="purchase_requisition",
            entity_id=submitted_requisition.id,
            module="inventory",
            details={
                "requisition_number": submitted_requisition.requisition_number,
                "approval_request_id": request.id,
                "note": normalize_optional_text(note),
            },
        )
        self._approval_service.publish_requested(request)
        domain_events.inventory_requisitions_changed.emit(submitted_requisition.id)
        return submitted_requisition

    def update_requisition(
        self,
        requisition_id: str,
        *,
        requesting_site_id: str | None = None,
        requesting_storeroom_id: str | None = None,
        purpose: str | None = None,
        needed_by_date: date | None = None,
        priority: str | None = None,
        source_reference_type: str | None = None,
        source_reference_id: str | None = None,
        source_module: str | None = None,
        source_entity_type: str | None = None,
        source_code_snapshot: str | None = None,
        source_title_snapshot: str | None = None,
        source_status_snapshot: str | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> PurchaseRequisition:
        self._require_manage("update purchase requisition")
        requisition = self._require_draft_requisition(requisition_id)
        if expected_version is not None and requisition.version != expected_version:
            raise ConcurrencyError(
                "Purchase requisition changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        organization = self._active_organization()
        next_site_id = normalize_optional_text(requesting_site_id) or requisition.requesting_site_id
        next_storeroom_id = normalize_optional_text(requesting_storeroom_id) or requisition.requesting_storeroom_id
        storeroom = self._inventory_service.get_storeroom(next_storeroom_id)
        if not storeroom.is_active:
            raise ValidationError(
                "Requesting storeroom must be active.",
                code="INVENTORY_REQUISITION_STOREROOM_INACTIVE",
            )
        if storeroom.site_id != next_site_id:
            raise ValidationError(
                "Requesting storeroom must belong to the selected site.",
                code="INVENTORY_REQUISITION_SITE_STOREROOM_MISMATCH",
            )
        if storeroom.organization_id != organization.id:
            raise ValidationError(
                "Requesting storeroom must belong to the active organization.",
                code="INVENTORY_REQUISITION_STOREROOM_SCOPE_INVALID",
            )
        requisition = replace(
            requisition,
            requesting_site_id=next_site_id,
            requesting_storeroom_id=next_storeroom_id,
            purpose=requisition.purpose if purpose is None else purpose,
            needed_by_date=normalize_optional_date(needed_by_date, label="Needed-by date"),
            priority=requisition.priority if priority is None else priority,
            source_reference_type=(
                requisition.source_reference_type
                if source_reference_type is None
                else source_reference_type
            ),
            source_reference_id=(
                requisition.source_reference_id
                if source_reference_id is None
                else source_reference_id
            ),
            source_module=requisition.source_module if source_module is None else source_module,
            source_entity_type=(
                requisition.source_entity_type
                if source_entity_type is None
                else source_entity_type
            ),
            source_code_snapshot=(
                requisition.source_code_snapshot
                if source_code_snapshot is None
                else source_code_snapshot
            ),
            source_title_snapshot=(
                requisition.source_title_snapshot
                if source_title_snapshot is None
                else source_title_snapshot
            ),
            source_status_snapshot=(
                requisition.source_status_snapshot
                if source_status_snapshot is None
                else source_status_snapshot
            ),
            notes=requisition.notes if notes is None else notes,
            updated_at=datetime.now(timezone.utc),
        )
        try:
            self._requisition_repo.update(requisition)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_activity(
            self,
            action="inventory_requisition.update",
            entity_type="purchase_requisition",
            entity_id=requisition.id,
            module="inventory",
            details={
                "requisition_number": requisition.requisition_number,
                "site_id": requisition.requesting_site_id,
                "storeroom_id": requisition.requesting_storeroom_id,
                "priority": requisition.priority,
            },
        )
        domain_events.inventory_requisitions_changed.emit(requisition.id)
        return requisition

    def cancel_requisition(
        self,
        requisition_id: str,
        *,
        note: str = "",
        expected_version: int | None = None,
    ) -> PurchaseRequisition:
        self._require_manage("cancel purchase requisition")
        requisition = self._require_draft_requisition(requisition_id)
        if expected_version is not None and requisition.version != expected_version:
            raise ConcurrencyError(
                "Purchase requisition changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        validate_transition(
            current_status=requisition.status.value,
            next_status=PurchaseRequisitionStatus.CANCELLED.value,
            transitions=REQUISITION_STATUS_TRANSITIONS,
        )
        effective_at = datetime.now(timezone.utc)
        requisition = replace(
            requisition,
            status=PurchaseRequisitionStatus.CANCELLED,
            cancelled_at=effective_at,
            updated_at=effective_at,
        )
        lines = self._requisition_line_repo.list_for_requisition(requisition.id)
        for line in lines:
            line = replace(line, status=PurchaseRequisitionLineStatus.CANCELLED)
            self._requisition_line_repo.update(line)
        try:
            self._requisition_repo.update(requisition)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_activity(
            self,
            action="inventory_requisition.cancel",
            entity_type="purchase_requisition",
            entity_id=requisition.id,
            module="inventory",
            details={
                "requisition_number": requisition.requisition_number,
                "note": normalize_optional_text(note),
            },
        )
        domain_events.inventory_requisitions_changed.emit(requisition.id)
        return requisition


__all__ = ["ProcurementLifecycleMixin"]
