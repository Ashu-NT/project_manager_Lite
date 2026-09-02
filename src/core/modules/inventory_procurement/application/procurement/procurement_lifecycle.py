from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError

from src.core.modules.inventory_procurement.application.common.support import (
    REQUISITION_STATUS_TRANSITIONS,
    normalize_optional_date,
    normalize_optional_text,
    resolve_item_uom_factor,
    validate_transition,
)
from src.core.modules.inventory_procurement.application.procurement.procurement_support import (
    build_requisition_number,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseRequisition,
    PurchaseRequisitionLine,
    PurchaseRequisitionLineStatus,
    PurchaseRequisitionStatus,
)
from src.core.modules.inventory_procurement.domain.procurement.requisition_events import (
    InventoryRequisitionCancelled,
    InventoryRequisitionCreated,
    InventoryRequisitionLineAdded,
    InventoryRequisitionProfileUpdated,
    InventoryRequisitionSubmitted,
)
from src.core.platform.application.approval.approval_mutation_participant import (
    request_approval_using,
)
from src.core.platform.common.ids import generate_id
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, ValidationError
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext


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
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="create purchase requisition"
        )
        occurred_at = datetime.now(timezone.utc)
        try:
            with self._require_requisition_uow_factory().create(
                context=DomainEventContext(correlation_id=generate_id())
            ) as uow:
                uow.requisitions.add(requisition)
                record_activity(
                    uow,
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
                    commit=False,
                )
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="purchase_requisition",
                    entity_id=requisition.id,
                    module="inventory",
                    severity="low",
                    metadata={
                        "requisition_number": requisition.requisition_number,
                        "site_id": requisition.requesting_site_id,
                        "storeroom_id": requisition.requesting_storeroom_id,
                    },
                    commit=False,
                    fail_closed=True,
                )
                uow.record_event(
                    InventoryRequisitionCreated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        requisition_id=requisition.id,
                        occurred_at=occurred_at,
                    )
                )
                uow.commit()
        except IntegrityError as exc:
            raise ValidationError(
                "Requisition number already exists.",
                code="INVENTORY_REQUISITION_NUMBER_EXISTS",
            ) from exc
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
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="add purchase requisition line"
        )
        occurred_at = datetime.now(timezone.utc)
        try:
            with self._require_requisition_uow_factory().create(
                context=DomainEventContext(correlation_id=generate_id())
            ) as uow:
                uow.requisition_lines.add(line)
                record_activity(
                    uow,
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
                    commit=False,
                )
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="purchase_requisition_line",
                    entity_id=line.id,
                    module="inventory",
                    severity="low",
                    metadata={
                        "requisition_id": requisition.id,
                        "line_number": str(line.line_number),
                        "stock_item_id": line.stock_item_id,
                    },
                    commit=False,
                    fail_closed=True,
                )
                uow.record_event(
                    InventoryRequisitionLineAdded(
                        tenant_id=tenant_id,
                        organization_id=requisition.organization_id,
                        requisition_id=requisition.id,
                        requisition_line_id=line.id,
                        occurred_at=occurred_at,
                    )
                )
                uow.commit()
        except IntegrityError as exc:
            raise ValidationError(
                "Requisition line already exists.",
                code="INVENTORY_REQUISITION_LINE_EXISTS",
            ) from exc
        return line

    def submit_requisition(self, requisition_id: str, *, note: str = "") -> PurchaseRequisition:
        if self._requisition_submission_uow_factory is None:
            raise BusinessRuleError(
                "Purchase requisition submission requires a configured transaction owner.",
                code="INVENTORY_REQUISITION_SUBMISSION_UOW_REQUIRED",
            )
        if self._clock is None:
            raise BusinessRuleError(
                "Purchase requisition submission requires a configured Clock.",
                code="INVENTORY_REQUISITION_CLOCK_REQUIRED",
            )
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
                clock=self._clock,
                record_event=uow.record_event,
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
            record_activity(
                uow,
                action="inventory_requisition.submit",
                entity_type="purchase_requisition",
                entity_id=submitted_requisition.id,
                module="inventory",
                details={
                    "requisition_number": submitted_requisition.requisition_number,
                    "approval_request_id": request.id,
                    "note": normalize_optional_text(note),
                },
                commit=False,
            )
            uow.record_event(
                InventoryRequisitionSubmitted(
                    tenant_id=tenant_id,
                    organization_id=submitted_requisition.organization_id,
                    requisition_id=submitted_requisition.id,
                    approval_request_id=request.id,
                    occurred_at=effective_at,
                )
            )
            uow.commit()
        self._approval_service.publish_requested(request)
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
        candidate = replace(
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
        )
        if candidate == requisition:
            return requisition
        now = datetime.now(timezone.utc)
        candidate = replace(candidate, updated_at=now)
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="update purchase requisition"
        )
        with self._require_requisition_uow_factory().create(
            context=DomainEventContext(correlation_id=generate_id())
        ) as uow:
            uow.requisitions.update(candidate)
            record_activity(
                uow,
                action="inventory_requisition.update",
                entity_type="purchase_requisition",
                entity_id=candidate.id,
                module="inventory",
                details={
                    "requisition_number": candidate.requisition_number,
                    "site_id": candidate.requesting_site_id,
                    "storeroom_id": candidate.requesting_storeroom_id,
                    "priority": candidate.priority,
                },
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="purchase_requisition",
                entity_id=candidate.id,
                module="inventory",
                severity="low",
                metadata={
                    "requisition_number": candidate.requisition_number,
                    "site_id": candidate.requesting_site_id,
                    "storeroom_id": candidate.requesting_storeroom_id,
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                InventoryRequisitionProfileUpdated(
                    tenant_id=tenant_id,
                    organization_id=candidate.organization_id,
                    requisition_id=candidate.id,
                    occurred_at=now,
                )
            )
            uow.commit()
        return candidate

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
        cancelled_requisition = replace(
            requisition,
            status=PurchaseRequisitionStatus.CANCELLED,
            cancelled_at=effective_at,
            updated_at=effective_at,
        )
        lines = self._requisition_line_repo.list_for_requisition(requisition.id)
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="cancel purchase requisition"
        )
        with self._require_requisition_uow_factory().create(
            context=DomainEventContext(correlation_id=generate_id())
        ) as uow:
            for line in lines:
                line = replace(line, status=PurchaseRequisitionLineStatus.CANCELLED)
                uow.requisition_lines.update(line)
            uow.requisitions.update(cancelled_requisition)
            record_activity(
                uow,
                action="inventory_requisition.cancel",
                entity_type="purchase_requisition",
                entity_id=cancelled_requisition.id,
                module="inventory",
                details={
                    "requisition_number": cancelled_requisition.requisition_number,
                    "note": normalize_optional_text(note),
                },
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="purchase_requisition",
                entity_id=cancelled_requisition.id,
                module="inventory",
                severity="medium",
                metadata={
                    "requisition_number": cancelled_requisition.requisition_number,
                    "action": "cancel",
                    "note": normalize_optional_text(note),
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                InventoryRequisitionCancelled(
                    tenant_id=tenant_id,
                    organization_id=cancelled_requisition.organization_id,
                    requisition_id=cancelled_requisition.id,
                    occurred_at=effective_at,
                )
            )
            uow.commit()
        return cancelled_requisition


__all__ = ["ProcurementLifecycleMixin"]
