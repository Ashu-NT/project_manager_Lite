from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError

from core.modules.inventory_procurement.domain import PurchaseRequisition, PurchaseRequisitionLine, PurchaseRequisitionLineStatus, PurchaseRequisitionStatus
from core.modules.inventory_procurement.services.procurement.procurement_support import build_requisition_number, normalize_priority
from core.modules.inventory_procurement.support import (
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
from src.core.platform.audit.helpers import record_audit
from src.core.platform.common.exceptions import ConcurrencyError, ValidationError
from src.core.platform.notifications.domain_events import domain_events


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
            purpose=normalize_optional_text(purpose),
            needed_by_date=normalize_optional_date(needed_by_date, label="Needed-by date"),
            priority=normalize_priority(priority),
            source_reference_type=normalize_source_reference_type(source_reference_type),
            source_reference_id=normalize_optional_text(source_reference_id),
            notes=normalize_optional_text(notes),
        )
        try:
            self._requisition_repo.add(requisition)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Requisition number already exists.", code="INVENTORY_REQUISITION_NUMBER_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_requisition.create",
            entity_type="purchase_requisition",
            entity_id=requisition.id,
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
        normalized_uom = normalize_uom(uom or item.stock_uom, label="Requisition line UOM")
        resolve_item_uom_factor(item, normalized_uom, label="Requisition line UOM")
        supplier_id = self._validate_supplier_reference(suggested_supplier_party_id)
        next_line_number = len(self._requisition_line_repo.list_for_requisition(requisition.id)) + 1
        line = PurchaseRequisitionLine.create(
            purchase_requisition_id=requisition.id,
            line_number=next_line_number,
            stock_item_id=item.id,
            description=normalize_optional_text(description) or item.name,
            quantity_requested=normalize_positive_quantity(quantity_requested, label="Requisition quantity"),
            uom=normalized_uom,
            needed_by_date=needed_by_date,
            estimated_unit_cost=normalize_nonnegative_quantity(estimated_unit_cost, label="Estimated unit cost"),
            suggested_supplier_party_id=supplier_id,
            status=PurchaseRequisitionLineStatus.DRAFT,
            notes=normalize_optional_text(notes),
        )
        try:
            self._requisition_line_repo.add(line)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Requisition line already exists.", code="INVENTORY_REQUISITION_LINE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_requisition_line.create",
            entity_type="purchase_requisition_line",
            entity_id=line.id,
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
        self._require_manage("submit purchase requisition")
        requisition = self._require_draft_requisition(requisition_id)
        lines = self._requisition_line_repo.list_for_requisition(requisition.id)
        if not lines:
            raise ValidationError(
                "Purchase requisition must have at least one line before submission.",
                code="INVENTORY_REQUISITION_LINES_REQUIRED",
            )
        request = self._approval_service.request_change(
            request_type="purchase_requisition.submit",
            entity_type="purchase_requisition",
            entity_id=requisition.id,
            project_id=None,
            payload={
                "requisition_id": requisition.id,
                "requisition_number": requisition.requisition_number,
                "site_id": requisition.requesting_site_id,
                "storeroom_id": requisition.requesting_storeroom_id,
                "purpose": requisition.purpose,
                "line_count": len(lines),
            },
            commit=False,
        )
        validate_transition(
            current_status=requisition.status.value,
            next_status=PurchaseRequisitionStatus.SUBMITTED.value,
            transitions=REQUISITION_STATUS_TRANSITIONS,
        )
        requisition.status = PurchaseRequisitionStatus.SUBMITTED
        requisition.approval_request_id = request.id
        requisition.submitted_at = datetime.now(timezone.utc)
        requisition.updated_at = requisition.submitted_at
        for line in lines:
            line.status = PurchaseRequisitionLineStatus.DRAFT
            self._requisition_line_repo.update(line)
        self._requisition_repo.update(requisition)
        self._session.commit()
        record_audit(
            self,
            action="inventory_requisition.submit",
            entity_type="purchase_requisition",
            entity_id=requisition.id,
            details={
                "requisition_number": requisition.requisition_number,
                "approval_request_id": request.id,
                "note": normalize_optional_text(note),
            },
        )
        domain_events.approvals_changed.emit(request.id)
        domain_events.inventory_requisitions_changed.emit(requisition.id)
        return requisition

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
        requisition.requesting_site_id = next_site_id
        requisition.requesting_storeroom_id = next_storeroom_id
        if purpose is not None:
            requisition.purpose = normalize_optional_text(purpose)
        requisition.needed_by_date = normalize_optional_date(needed_by_date, label="Needed-by date")
        if priority is not None:
            requisition.priority = normalize_priority(priority)
        if source_reference_type is not None:
            requisition.source_reference_type = normalize_source_reference_type(source_reference_type)
        if source_reference_id is not None:
            requisition.source_reference_id = normalize_optional_text(source_reference_id)
        if notes is not None:
            requisition.notes = normalize_optional_text(notes)
        requisition.updated_at = datetime.now(timezone.utc)
        try:
            self._requisition_repo.update(requisition)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_requisition.update",
            entity_type="purchase_requisition",
            entity_id=requisition.id,
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
        requisition.status = PurchaseRequisitionStatus.CANCELLED
        requisition.cancelled_at = effective_at
        requisition.updated_at = effective_at
        lines = self._requisition_line_repo.list_for_requisition(requisition.id)
        for line in lines:
            line.status = PurchaseRequisitionLineStatus.CANCELLED
            self._requisition_line_repo.update(line)
        try:
            self._requisition_repo.update(requisition)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_requisition.cancel",
            entity_type="purchase_requisition",
            entity_id=requisition.id,
            details={
                "requisition_number": requisition.requisition_number,
                "note": normalize_optional_text(note),
            },
        )
        domain_events.inventory_requisitions_changed.emit(requisition.id)
        return requisition


__all__ = ["ProcurementLifecycleMixin"]
