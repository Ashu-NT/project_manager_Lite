from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.inventory_procurement.services.inventory import InventoryService
from core.modules.inventory_procurement.services.item_master import ItemMasterService
from core.modules.inventory_procurement.services.maintenance_integration import MaintenanceMaterialService
from core.modules.inventory_procurement.services.maintenance_integration.contracts import (
    MaintenanceMaterialAvailability,
    MaintenanceMaterialAvailabilityStatus,
    MaintenanceMaterialProcurementEscalation,
)
from core.modules.maintenance_management.domain import (
    MaintenanceMaterialProcurementStatus,
    MaintenanceWorkOrder,
    MaintenanceWorkOrderMaterialRequirement,
    MaintenanceWorkOrderStatus,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceWorkOrderMaterialRequirementRepository,
    MaintenanceWorkOrderRepository,
)
from core.modules.maintenance_management.support import coerce_optional_decimal, normalize_optional_text
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization


_MATERIAL_SOURCE_TYPE = "maintenance_material_demand"


class MaintenanceWorkOrderMaterialRequirementService:
    def __init__(
        self,
        session: Session,
        material_requirement_repo: MaintenanceWorkOrderMaterialRequirementRepository,
        *,
        organization_repo: OrganizationRepository,
        work_order_repo: MaintenanceWorkOrderRepository,
        item_service: ItemMasterService | None = None,
        inventory_service: InventoryService | None = None,
        maintenance_material_service: MaintenanceMaterialService | None = None,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._material_requirement_repo = material_requirement_repo
        self._organization_repo = organization_repo
        self._work_order_repo = work_order_repo
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._maintenance_material_service = maintenance_material_service
        self._user_session = user_session
        self._audit_service = audit_service

    def list_requirements(
        self,
        *,
        work_order_id: str | None = None,
        procurement_status: str | None = None,
        preferred_storeroom_id: str | None = None,
        stock_item_id: str | None = None,
    ) -> list[MaintenanceWorkOrderMaterialRequirement]:
        self._require_read("list maintenance material requirements")
        organization = self._active_organization()
        if work_order_id is not None:
            self._get_work_order(work_order_id, organization=organization)
        rows = self._material_requirement_repo.list_for_organization(
            organization.id,
            work_order_id=work_order_id,
            procurement_status=(str(procurement_status or "").strip().upper() or None),
            preferred_storeroom_id=(str(preferred_storeroom_id or "").strip() or None),
            stock_item_id=(str(stock_item_id or "").strip() or None),
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for,
        )

    def get_requirement(self, material_requirement_id: str) -> MaintenanceWorkOrderMaterialRequirement:
        self._require_read("view maintenance material requirement")
        organization = self._active_organization()
        requirement = self._material_requirement_repo.get(material_requirement_id)
        if requirement is None or requirement.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance material requirement not found in the active organization.",
                code="MAINTENANCE_MATERIAL_REQUIREMENT_NOT_FOUND",
            )
        self._require_scope_read(
            self._scope_anchor_for(requirement),
            operation_label="view maintenance material requirement",
        )
        return requirement

    def create_requirement(
        self,
        *,
        work_order_id: str,
        stock_item_id: str | None = None,
        description: str = "",
        required_qty=None,
        required_uom: str = "",
        issued_qty=None,
        is_stock_item: bool = True,
        preferred_storeroom_id: str | None = None,
        notes: str = "",
    ) -> MaintenanceWorkOrderMaterialRequirement:
        self._require_manage("create maintenance material requirement")
        organization = self._active_organization()
        work_order = self._get_work_order(work_order_id, organization=organization)
        self._ensure_work_order_is_mutable(work_order)
        normalized_stock_item_id = (str(stock_item_id or "").strip() or None)
        normalized_storeroom_id = (str(preferred_storeroom_id or "").strip() or None)
        resolved_required_qty = self._coerce_positive_decimal(required_qty, label="Required quantity")
        resolved_issued_qty = coerce_optional_decimal(issued_qty, label="Issued quantity") or Decimal("0")
        normalized_uom = self._normalize_required_uom(required_uom)
        normalized_description = normalize_optional_text(description)

        item = None
        if is_stock_item:
            if normalized_stock_item_id is None:
                raise ValidationError(
                    "Stock item is required for stock-based maintenance material demand.",
                    code="MAINTENANCE_MATERIAL_STOCK_ITEM_REQUIRED",
                )
            if normalized_storeroom_id is None:
                raise ValidationError(
                    "Preferred storeroom is required for stock-based maintenance material demand.",
                    code="MAINTENANCE_MATERIAL_STOREROOM_REQUIRED",
                )
            item = self._get_item_for_internal_use(normalized_stock_item_id)
            storeroom = self._get_storeroom_for_internal_use(normalized_storeroom_id)
            if storeroom.site_id != work_order.site_id:
                raise ValidationError(
                    "Preferred storeroom must belong to the same site as the work order.",
                    code="MAINTENANCE_MATERIAL_STOREROOM_SITE_MISMATCH",
                )
            if not normalized_uom:
                normalized_uom = (item.issue_uom or item.stock_uom or "").strip().upper()
            if not normalized_description:
                normalized_description = item.name
        else:
            normalized_stock_item_id = None
            normalized_storeroom_id = None

        if not normalized_uom:
            raise ValidationError(
                "Required UOM is required for maintenance material demand.",
                code="MAINTENANCE_MATERIAL_REQUIRED_UOM_REQUIRED",
            )
        if not normalized_description:
            raise ValidationError(
                "Description is required for maintenance material demand.",
                code="MAINTENANCE_MATERIAL_DESCRIPTION_REQUIRED",
            )
        if resolved_issued_qty > resolved_required_qty:
            raise ValidationError(
                "Issued quantity cannot exceed required quantity.",
                code="MAINTENANCE_MATERIAL_ISSUED_QTY_EXCEEDS_REQUIRED",
            )

        requirement = MaintenanceWorkOrderMaterialRequirement.create(
            organization_id=organization.id,
            work_order_id=work_order.id,
            stock_item_id=normalized_stock_item_id,
            description=normalized_description,
            required_qty=resolved_required_qty,
            issued_qty=resolved_issued_qty,
            required_uom=normalized_uom,
            is_stock_item=bool(is_stock_item),
            preferred_storeroom_id=normalized_storeroom_id,
            procurement_status=self._derive_base_procurement_status(
                is_stock_item=bool(is_stock_item),
                required_qty=resolved_required_qty,
                issued_qty=resolved_issued_qty,
                linked_requisition_id=None,
            ),
            notes=normalize_optional_text(notes),
        )
        try:
            self._material_requirement_repo.add(requirement)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Maintenance material requirement could not be saved.",
                code="MAINTENANCE_MATERIAL_REQUIREMENT_SAVE_FAILED",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_material_requirement.create", requirement)
        return requirement

    def update_requirement(
        self,
        material_requirement_id: str,
        *,
        stock_item_id: str | None = None,
        description: str | None = None,
        required_qty=None,
        required_uom: str | None = None,
        issued_qty=None,
        is_stock_item: bool | None = None,
        preferred_storeroom_id: str | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceWorkOrderMaterialRequirement:
        self._require_manage("update maintenance material requirement")
        requirement = self.get_requirement(material_requirement_id)
        organization = self._active_organization()
        work_order = self._get_work_order(requirement.work_order_id, organization=organization)
        self._ensure_work_order_is_mutable(work_order)
        if expected_version is not None and requirement.version != expected_version:
            raise ConcurrencyError(
                "Maintenance material requirement changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        next_is_stock_item = requirement.is_stock_item if is_stock_item is None else bool(is_stock_item)
        next_stock_item_id = requirement.stock_item_id
        next_storeroom_id = requirement.preferred_storeroom_id
        next_required_uom = requirement.required_uom
        next_description = requirement.description

        if stock_item_id is not None:
            next_stock_item_id = (str(stock_item_id or "").strip() or None)
        if preferred_storeroom_id is not None:
            next_storeroom_id = (str(preferred_storeroom_id or "").strip() or None)
        if required_uom is not None:
            next_required_uom = self._normalize_required_uom(required_uom)
        if description is not None:
            next_description = normalize_optional_text(description)
        if required_qty is not None:
            requirement.required_qty = self._coerce_positive_decimal(required_qty, label="Required quantity")
        if issued_qty is not None:
            requirement.issued_qty = coerce_optional_decimal(issued_qty, label="Issued quantity") or Decimal("0")
        if requirement.issued_qty > requirement.required_qty:
            raise ValidationError(
                "Issued quantity cannot exceed required quantity.",
                code="MAINTENANCE_MATERIAL_ISSUED_QTY_EXCEEDS_REQUIRED",
            )

        if next_is_stock_item:
            if next_stock_item_id is None:
                raise ValidationError(
                    "Stock item is required for stock-based maintenance material demand.",
                    code="MAINTENANCE_MATERIAL_STOCK_ITEM_REQUIRED",
                )
            if next_storeroom_id is None:
                raise ValidationError(
                    "Preferred storeroom is required for stock-based maintenance material demand.",
                    code="MAINTENANCE_MATERIAL_STOREROOM_REQUIRED",
                )
            item = self._get_item_for_internal_use(next_stock_item_id)
            storeroom = self._get_storeroom_for_internal_use(next_storeroom_id)
            if storeroom.site_id != work_order.site_id:
                raise ValidationError(
                    "Preferred storeroom must belong to the same site as the work order.",
                    code="MAINTENANCE_MATERIAL_STOREROOM_SITE_MISMATCH",
                )
            if not next_required_uom:
                next_required_uom = (item.issue_uom or item.stock_uom or "").strip().upper()
            if not next_description:
                next_description = item.name
        else:
            next_stock_item_id = None
            next_storeroom_id = None
            requirement.last_availability_status = ""
            requirement.last_missing_qty = None
            requirement.linked_requisition_id = None

        if not next_required_uom:
            raise ValidationError(
                "Required UOM is required for maintenance material demand.",
                code="MAINTENANCE_MATERIAL_REQUIRED_UOM_REQUIRED",
            )
        if not next_description:
            raise ValidationError(
                "Description is required for maintenance material demand.",
                code="MAINTENANCE_MATERIAL_DESCRIPTION_REQUIRED",
            )

        requirement.stock_item_id = next_stock_item_id
        requirement.description = next_description
        requirement.required_uom = next_required_uom
        requirement.is_stock_item = next_is_stock_item
        requirement.preferred_storeroom_id = next_storeroom_id
        if notes is not None:
            requirement.notes = normalize_optional_text(notes)
        requirement.procurement_status = self._derive_base_procurement_status(
            is_stock_item=requirement.is_stock_item,
            required_qty=requirement.required_qty,
            issued_qty=requirement.issued_qty,
            linked_requisition_id=requirement.linked_requisition_id,
        )
        requirement.updated_at = datetime.now(timezone.utc)
        try:
            self._material_requirement_repo.update(requirement)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Maintenance material requirement could not be updated.",
                code="MAINTENANCE_MATERIAL_REQUIREMENT_SAVE_FAILED",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_material_requirement.update", requirement)
        return requirement

    def get_requirement_availability(self, material_requirement_id: str) -> MaintenanceMaterialAvailability:
        self._require_read("view maintenance material availability")
        requirement = self.get_requirement(material_requirement_id)
        return self._resolve_availability(requirement)

    def refresh_requirement_availability(
        self,
        material_requirement_id: str,
        *,
        expected_version: int | None = None,
    ) -> MaintenanceWorkOrderMaterialRequirement:
        self._require_manage("refresh maintenance material availability")
        requirement = self.get_requirement(material_requirement_id)
        organization = self._active_organization()
        work_order = self._get_work_order(requirement.work_order_id, organization=organization)
        self._ensure_work_order_is_mutable(work_order)
        if expected_version is not None and requirement.version != expected_version:
            raise ConcurrencyError(
                "Maintenance material requirement changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

        if not requirement.is_stock_item:
            requirement.procurement_status = MaintenanceMaterialProcurementStatus.NON_STOCK
            requirement.last_availability_status = "NON_STOCK"
            requirement.last_missing_qty = None
        else:
            availability = self._resolve_availability(requirement)
            requirement.last_availability_status = availability.status.value
            requirement.last_missing_qty = Decimal(str(availability.missing_stock_qty))
            requirement.procurement_status = self._derive_procurement_status_from_availability(requirement, availability)
        requirement.updated_at = datetime.now(timezone.utc)
        try:
            self._material_requirement_repo.update(requirement)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_material_requirement.refresh", requirement)
        return requirement

    def escalate_requirement_shortage(
        self,
        material_requirement_id: str,
        *,
        needed_by_date=None,
        priority: str = "NORMAL",
        notes: str = "",
        auto_submit: bool = False,
        expected_version: int | None = None,
    ) -> MaintenanceMaterialProcurementEscalation:
        self._require_manage("escalate maintenance material shortage")
        requirement = self.get_requirement(material_requirement_id)
        organization = self._active_organization()
        work_order = self._get_work_order(requirement.work_order_id, organization=organization)
        self._ensure_work_order_is_mutable(work_order)
        if expected_version is not None and requirement.version != expected_version:
            raise ConcurrencyError(
                "Maintenance material requirement changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if not requirement.is_stock_item:
            raise ValidationError(
                "Non-stock maintenance material demand cannot be escalated through inventory procurement.",
                code="MAINTENANCE_MATERIAL_NON_STOCK_ESCALATION_INVALID",
            )
        if self._maintenance_material_service is None:
            raise ValidationError(
                "Maintenance material contract service is not configured.",
                code="MAINTENANCE_MATERIAL_CONTRACT_UNAVAILABLE",
            )
        if requirement.stock_item_id is None or requirement.preferred_storeroom_id is None:
            raise ValidationError(
                "Stock item and preferred storeroom are required before escalating maintenance demand.",
                code="MAINTENANCE_MATERIAL_INVENTORY_LINKS_REQUIRED",
            )

        escalation = self._maintenance_material_service.escalate_shortage_to_requisition(
            stock_item_id=requirement.stock_item_id,
            storeroom_id=requirement.preferred_storeroom_id,
            quantity=float(requirement.required_qty),
            uom=requirement.required_uom,
            source_reference_type=_MATERIAL_SOURCE_TYPE,
            source_reference_id=requirement.id,
            needed_by_date=needed_by_date,
            priority=priority,
            notes=notes or requirement.notes,
            auto_submit=auto_submit,
        )
        requirement.linked_requisition_id = escalation.requisition.id
        requirement.last_availability_status = escalation.availability.status.value
        requirement.last_missing_qty = Decimal(str(escalation.availability.missing_stock_qty))
        requirement.procurement_status = MaintenanceMaterialProcurementStatus.REQUISITIONED
        requirement.updated_at = datetime.now(timezone.utc)
        try:
            self._material_requirement_repo.update(requirement)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_material_requirement.escalate", requirement)
        return escalation

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _get_work_order(self, work_order_id: str, *, organization: Organization) -> MaintenanceWorkOrder:
        work_order = self._work_order_repo.get(work_order_id)
        if work_order is None or work_order.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance work order not found in the active organization.",
                code="MAINTENANCE_WORK_ORDER_NOT_FOUND",
            )
        return work_order

    def _ensure_work_order_is_mutable(self, work_order: MaintenanceWorkOrder) -> None:
        if work_order.status in {MaintenanceWorkOrderStatus.CANCELLED, MaintenanceWorkOrderStatus.CLOSED}:
            raise BusinessRuleError(
                "Material requirements cannot be changed once the work order is cancelled or closed.",
                code="MAINTENANCE_WORK_ORDER_NOT_MUTABLE",
            )

    def _get_item_for_internal_use(self, stock_item_id: str):
        if self._item_service is None:
            raise ValidationError(
                "Inventory item service is not configured for maintenance material planning.",
                code="MAINTENANCE_MATERIAL_ITEM_SERVICE_UNAVAILABLE",
            )
        getter = getattr(self._item_service, "get_item_for_internal_use", None)
        if callable(getter):
            return getter(stock_item_id)
        return self._item_service.get_item(stock_item_id)

    def _get_storeroom_for_internal_use(self, storeroom_id: str):
        if self._inventory_service is None:
            raise ValidationError(
                "Inventory storeroom service is not configured for maintenance material planning.",
                code="MAINTENANCE_MATERIAL_STOREROOM_SERVICE_UNAVAILABLE",
            )
        getter = getattr(self._inventory_service, "get_storeroom_for_internal_use", None)
        if callable(getter):
            return getter(storeroom_id)
        return self._inventory_service.get_storeroom(storeroom_id)

    def _normalize_required_uom(self, required_uom: str | None) -> str:
        return normalize_optional_text(required_uom).upper()

    def _coerce_positive_decimal(self, value, *, label: str) -> Decimal:
        resolved = coerce_optional_decimal(value, label=label)
        if resolved is None or resolved <= 0:
            raise ValidationError(
                f"{label} must be greater than zero.",
                code=f"{label.upper().replace(' ', '_')}_POSITIVE_REQUIRED",
            )
        return resolved

    def _resolve_availability(
        self,
        requirement: MaintenanceWorkOrderMaterialRequirement,
    ) -> MaintenanceMaterialAvailability:
        if not requirement.is_stock_item:
            raise ValidationError(
                "Non-stock maintenance material demand does not have inventory availability.",
                code="MAINTENANCE_MATERIAL_AVAILABILITY_NOT_APPLICABLE",
            )
        if self._maintenance_material_service is None:
            raise ValidationError(
                "Maintenance material contract service is not configured.",
                code="MAINTENANCE_MATERIAL_CONTRACT_UNAVAILABLE",
            )
        if requirement.stock_item_id is None or requirement.preferred_storeroom_id is None:
            raise ValidationError(
                "Stock item and preferred storeroom are required before checking availability.",
                code="MAINTENANCE_MATERIAL_INVENTORY_LINKS_REQUIRED",
            )
        return self._maintenance_material_service.get_material_availability(
            stock_item_id=requirement.stock_item_id,
            storeroom_id=requirement.preferred_storeroom_id,
            quantity=float(requirement.required_qty),
            uom=requirement.required_uom,
            source_reference_type=_MATERIAL_SOURCE_TYPE,
            source_reference_id=requirement.id,
        )

    def _derive_base_procurement_status(
        self,
        *,
        is_stock_item: bool,
        required_qty: Decimal,
        issued_qty: Decimal,
        linked_requisition_id: str | None,
    ) -> MaintenanceMaterialProcurementStatus:
        if not is_stock_item:
            return MaintenanceMaterialProcurementStatus.NON_STOCK
        if issued_qty >= required_qty:
            return MaintenanceMaterialProcurementStatus.FULLY_ISSUED
        if issued_qty > 0:
            return MaintenanceMaterialProcurementStatus.PARTIALLY_ISSUED
        if linked_requisition_id:
            return MaintenanceMaterialProcurementStatus.REQUISITIONED
        return MaintenanceMaterialProcurementStatus.PLANNED

    def _derive_procurement_status_from_availability(
        self,
        requirement: MaintenanceWorkOrderMaterialRequirement,
        availability: MaintenanceMaterialAvailability,
    ) -> MaintenanceMaterialProcurementStatus:
        base = self._derive_base_procurement_status(
            is_stock_item=requirement.is_stock_item,
            required_qty=requirement.required_qty,
            issued_qty=requirement.issued_qty,
            linked_requisition_id=requirement.linked_requisition_id,
        )
        if base != MaintenanceMaterialProcurementStatus.PLANNED:
            return base
        if availability.status == MaintenanceMaterialAvailabilityStatus.AVAILABLE_FROM_STOCK:
            return MaintenanceMaterialProcurementStatus.AVAILABLE_FROM_STOCK
        return MaintenanceMaterialProcurementStatus.SHORTAGE_IDENTIFIED

    def _scope_anchor_for(self, requirement: MaintenanceWorkOrderMaterialRequirement) -> str:
        work_order = self._work_order_repo.get(requirement.work_order_id)
        if work_order is None:
            return ""
        if work_order.asset_id:
            return work_order.asset_id
        if work_order.system_id:
            return work_order.system_id
        if work_order.location_id:
            return work_order.location_id
        return ""

    def _require_scope_read(self, scope_id: str, *, operation_label: str) -> None:
        if scope_id:
            require_scope_permission(
                self._user_session,
                "maintenance",
                scope_id,
                "maintenance.read",
                operation_label=operation_label,
            )
            return
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. The record is not anchored to a maintenance scope grant.",
                code="PERMISSION_DENIED",
            )

    def _record_change(self, action: str, requirement: MaintenanceWorkOrderMaterialRequirement) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_material_requirement",
            entity_id=requirement.id,
            details={
                "organization_id": requirement.organization_id,
                "work_order_id": requirement.work_order_id,
                "stock_item_id": requirement.stock_item_id,
                "required_qty": str(requirement.required_qty),
                "issued_qty": str(requirement.issued_qty),
                "required_uom": requirement.required_uom,
                "is_stock_item": requirement.is_stock_item,
                "preferred_storeroom_id": requirement.preferred_storeroom_id,
                "procurement_status": requirement.procurement_status.value,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_material_requirement",
                entity_id=requirement.id,
                source_event="maintenance_material_requirements_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceWorkOrderMaterialRequirementService"]
