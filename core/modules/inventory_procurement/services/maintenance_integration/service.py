from __future__ import annotations

from core.modules.inventory_procurement.domain import PurchaseRequisition, StockReservation
from core.modules.inventory_procurement.services.inventory import InventoryService
from core.modules.inventory_procurement.services.item_master import ItemCategoryService, ItemMasterService
from core.modules.inventory_procurement.services.maintenance_integration.contracts import (
    MaintenanceMaterialAvailability,
    MaintenanceMaterialAvailabilityStatus,
    MaintenanceMaterialExecutionResult,
    MaintenanceMaterialProcurementEscalation,
)
from core.modules.inventory_procurement.services.procurement import ProcurementService
from core.modules.inventory_procurement.services.reservation import ReservationService
from core.modules.inventory_procurement.services.stock_control import StockControlService
from core.modules.inventory_procurement.support import (
    convert_item_quantity,
    normalize_maintenance_source_reference_type,
    normalize_optional_text,
    normalize_positive_quantity,
    normalize_uom,
)
from core.platform.common.exceptions import ValidationError
from src.core.platform.notifications.domain_events import domain_events


class MaintenanceMaterialService:
    """Inventory-owned contract surface for future maintenance material planning and execution."""

    def __init__(
        self,
        *,
        item_service: ItemMasterService,
        item_category_service: ItemCategoryService,
        inventory_service: InventoryService,
        stock_service: StockControlService,
        reservation_service: ReservationService,
        procurement_service: ProcurementService,
    ) -> None:
        self._item_service = item_service
        self._item_category_service = item_category_service
        self._inventory_service = inventory_service
        self._stock_service = stock_service
        self._reservation_service = reservation_service
        self._procurement_service = procurement_service

    def get_material_availability(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        source_reference_type: str,
        source_reference_id: str,
    ) -> MaintenanceMaterialAvailability:
        item, storeroom, normalized_source_type, normalized_source_id, normalized_qty, normalized_uom = (
            self._resolve_maintenance_request(
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
                quantity=quantity,
                uom=uom,
                source_reference_type=source_reference_type,
                source_reference_id=source_reference_id,
            )
        )
        maintenance_enabled = self._is_item_maintenance_enabled(item.category_code)
        requested_stock_qty = convert_item_quantity(
            item,
            normalized_qty,
            from_uom=normalized_uom,
            to_uom=item.stock_uom,
            label="Maintenance material UOM",
        )
        balance = self._stock_service.get_balance_for_stock_position(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
        )
        on_hand = float(getattr(balance, "on_hand_qty", 0.0) or 0.0)
        reserved = float(getattr(balance, "reserved_qty", 0.0) or 0.0)
        available = float(getattr(balance, "available_qty", 0.0) or 0.0)
        on_order = float(getattr(balance, "on_order_qty", 0.0) or 0.0)
        missing = max(0.0, requested_stock_qty - available)
        status = self._resolve_availability_status(
            maintenance_enabled=maintenance_enabled,
            item_is_stocked=item.is_stocked,
            item_is_purchase_allowed=item.is_purchase_allowed,
            requested_stock_qty=requested_stock_qty,
            available_stock_qty=available,
        )
        return MaintenanceMaterialAvailability(
            source_reference_type=normalized_source_type,
            source_reference_id=normalized_source_id,
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            requested_qty=normalized_qty,
            requested_uom=normalized_uom,
            requested_stock_qty=requested_stock_qty,
            on_hand_stock_qty=on_hand,
            reserved_stock_qty=reserved,
            available_stock_qty=available,
            on_order_stock_qty=on_order,
            missing_stock_qty=missing,
            status=status,
            can_reserve=status == MaintenanceMaterialAvailabilityStatus.AVAILABLE_FROM_STOCK,
            can_issue_from_stock=status in {
                MaintenanceMaterialAvailabilityStatus.AVAILABLE_FROM_STOCK,
                MaintenanceMaterialAvailabilityStatus.PARTIALLY_AVAILABLE_FROM_STOCK,
            },
            can_direct_procure=bool(item.is_purchase_allowed and missing > 0),
        )

    def reserve_material(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        need_by_date=None,
        source_reference_type: str,
        source_reference_id: str,
        notes: str = "",
    ) -> MaintenanceMaterialExecutionResult:
        availability = self.get_material_availability(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            quantity=quantity,
            uom=uom,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
        )
        self._require_maintenance_enabled(availability)
        if availability.status != MaintenanceMaterialAvailabilityStatus.AVAILABLE_FROM_STOCK:
            raise ValidationError(
                "Requested maintenance material is not fully available for reservation from stock.",
                code="INVENTORY_MAINTENANCE_STOCK_UNAVAILABLE",
            )
        reservation = self._reservation_service.create_reservation(
            stock_item_id=availability.stock_item_id,
            storeroom_id=availability.storeroom_id,
            reserved_qty=availability.requested_qty,
            uom=availability.requested_uom,
            need_by_date=need_by_date,
            source_reference_type=availability.source_reference_type,
            source_reference_id=availability.source_reference_id,
            notes=notes,
        )
        self._emit_material_event(availability.source_reference_type, availability.source_reference_id)
        return MaintenanceMaterialExecutionResult(
            source_reference_type=availability.source_reference_type,
            source_reference_id=availability.source_reference_id,
            availability=availability,
            reservation=reservation,
        )

    def issue_reserved_material(
        self,
        *,
        reservation_id: str,
        quantity: float,
        note: str = "",
    ) -> MaintenanceMaterialExecutionResult:
        reservation = self._reservation_service.get_reservation(reservation_id)
        normalized_source_type = normalize_maintenance_source_reference_type(reservation.source_reference_type)
        normalized_source_id = self._require_source_reference_id(reservation.source_reference_id)
        updated = self._reservation_service.issue_reserved_stock(
            reservation_id,
            quantity=quantity,
            note=note,
        )
        availability = self.get_material_availability(
            stock_item_id=updated.stock_item_id,
            storeroom_id=updated.storeroom_id,
            quantity=quantity,
            uom=updated.uom,
            source_reference_type=normalized_source_type,
            source_reference_id=normalized_source_id,
        )
        self._emit_material_event(normalized_source_type, normalized_source_id)
        return MaintenanceMaterialExecutionResult(
            source_reference_type=normalized_source_type,
            source_reference_id=normalized_source_id,
            availability=availability,
            reservation=updated,
        )

    def return_material(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        source_reference_type: str,
        source_reference_id: str,
        notes: str = "",
    ) -> MaintenanceMaterialExecutionResult:
        availability = self.get_material_availability(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            quantity=quantity,
            uom=uom,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
        )
        transaction = self._stock_service.return_stock(
            stock_item_id=availability.stock_item_id,
            storeroom_id=availability.storeroom_id,
            quantity=availability.requested_qty,
            uom=availability.requested_uom,
            reference_type=availability.source_reference_type,
            reference_id=availability.source_reference_id,
            notes=notes,
        )
        self._emit_material_event(availability.source_reference_type, availability.source_reference_id)
        return MaintenanceMaterialExecutionResult(
            source_reference_type=availability.source_reference_type,
            source_reference_id=availability.source_reference_id,
            availability=availability,
            transaction=transaction,
        )

    def escalate_shortage_to_requisition(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        source_reference_type: str,
        source_reference_id: str,
        needed_by_date=None,
        priority: str = "NORMAL",
        notes: str = "",
        auto_submit: bool = False,
    ) -> MaintenanceMaterialProcurementEscalation:
        availability = self.get_material_availability(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            quantity=quantity,
            uom=uom,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
        )
        self._require_maintenance_enabled(availability)
        if availability.missing_stock_qty <= 0:
            raise ValidationError(
                "Maintenance material is already fully available from stock.",
                code="INVENTORY_MAINTENANCE_SHORTAGE_NOT_FOUND",
            )
        item = self._item_service.get_item_for_internal_use(availability.stock_item_id)
        storeroom = self._inventory_service.get_storeroom_for_internal_use(availability.storeroom_id)
        if not item.is_purchase_allowed:
            raise ValidationError(
                "Selected maintenance material cannot be escalated to procurement.",
                code="INVENTORY_MAINTENANCE_PROCUREMENT_FORBIDDEN",
            )
        requisition = self._procurement_service.create_requisition(
            requesting_site_id=storeroom.site_id,
            requesting_storeroom_id=storeroom.id,
            purpose=f"Maintenance material demand for {availability.source_reference_type}:{availability.source_reference_id}",
            needed_by_date=needed_by_date,
            priority=priority,
            source_reference_type=availability.source_reference_type,
            source_reference_id=availability.source_reference_id,
            notes=notes,
        )
        requested_missing_qty = (
            convert_item_quantity(
                item,
                availability.missing_stock_qty,
                from_uom=item.stock_uom,
                to_uom=availability.requested_uom,
                label="Maintenance material UOM",
            )
            if availability.requested_uom != item.stock_uom
            else availability.missing_stock_qty
        )
        line = self._procurement_service.add_requisition_line(
            requisition.id,
            stock_item_id=item.id,
            quantity_requested=requested_missing_qty,
            uom=availability.requested_uom,
            description=f"Maintenance shortage for {availability.source_reference_type}:{availability.source_reference_id}",
            needed_by_date=needed_by_date,
            notes=notes,
        )
        if auto_submit:
            requisition = self._procurement_service.submit_requisition(requisition.id, note="Auto-submitted from maintenance material escalation")
        self._emit_material_event(availability.source_reference_type, availability.source_reference_id)
        return MaintenanceMaterialProcurementEscalation(
            source_reference_type=availability.source_reference_type,
            source_reference_id=availability.source_reference_id,
            availability=availability,
            requisition=requisition,
            requisition_line=line,
            auto_submitted=bool(auto_submit),
        )

    def list_reservations_for_source(
        self,
        *,
        source_reference_type: str,
        source_reference_id: str,
        include_closed: bool = True,
        limit: int = 200,
    ) -> list[StockReservation]:
        normalized_source_type = normalize_maintenance_source_reference_type(source_reference_type)
        normalized_source_id = self._require_source_reference_id(source_reference_id)
        rows = self._reservation_service.list_reservations(limit=limit)
        if include_closed:
            return [
                row
                for row in rows
                if row.source_reference_type == normalized_source_type and row.source_reference_id == normalized_source_id
            ]
        return [
            row
            for row in rows
            if row.source_reference_type == normalized_source_type
            and row.source_reference_id == normalized_source_id
            and row.status.value not in {"RELEASED", "CANCELLED", "FULLY_ISSUED"}
        ]

    def list_requisitions_for_source(
        self,
        *,
        source_reference_type: str,
        source_reference_id: str,
        limit: int = 200,
    ) -> list[PurchaseRequisition]:
        normalized_source_type = normalize_maintenance_source_reference_type(source_reference_type)
        normalized_source_id = self._require_source_reference_id(source_reference_id)
        rows = self._procurement_service.list_requisitions(limit=limit)
        return [
            row
            for row in rows
            if row.source_reference_type == normalized_source_type and row.source_reference_id == normalized_source_id
        ]

    def _resolve_maintenance_request(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None,
        source_reference_type: str,
        source_reference_id: str,
    ):
        item = self._item_service.get_item_for_internal_use(stock_item_id)
        storeroom = self._inventory_service.get_storeroom_for_internal_use(storeroom_id)
        normalized_source_type = normalize_maintenance_source_reference_type(source_reference_type)
        normalized_source_id = self._require_source_reference_id(source_reference_id)
        normalized_qty = normalize_positive_quantity(quantity, label="Maintenance material quantity")
        normalized_uom = normalize_uom(uom or item.issue_uom or item.stock_uom, label="Maintenance material UOM")
        if not item.is_active:
            raise ValidationError("Maintenance material item must be active.", code="INVENTORY_MAINTENANCE_ITEM_INACTIVE")
        if not storeroom.is_active:
            raise ValidationError("Maintenance material storeroom must be active.", code="INVENTORY_MAINTENANCE_STOREROOM_INACTIVE")
        return item, storeroom, normalized_source_type, normalized_source_id, normalized_qty, normalized_uom

    def _is_item_maintenance_enabled(self, category_code: str) -> bool:
        normalized_code = normalize_optional_text(category_code).upper()
        if not normalized_code:
            return True
        category = self._item_category_service.find_category_by_code(normalized_code, active_only=True)
        return bool(category is not None and category.supports_maintenance_usage)

    @staticmethod
    def _resolve_availability_status(
        *,
        maintenance_enabled: bool,
        item_is_stocked: bool,
        item_is_purchase_allowed: bool,
        requested_stock_qty: float,
        available_stock_qty: float,
    ) -> MaintenanceMaterialAvailabilityStatus:
        if not maintenance_enabled:
            return MaintenanceMaterialAvailabilityStatus.NOT_MAINTENANCE_ENABLED
        if not item_is_stocked and item_is_purchase_allowed:
            return MaintenanceMaterialAvailabilityStatus.DIRECT_PROCUREMENT_ONLY
        if available_stock_qty >= requested_stock_qty > 0:
            return MaintenanceMaterialAvailabilityStatus.AVAILABLE_FROM_STOCK
        if available_stock_qty > 0:
            return MaintenanceMaterialAvailabilityStatus.PARTIALLY_AVAILABLE_FROM_STOCK
        return MaintenanceMaterialAvailabilityStatus.UNAVAILABLE_FROM_STOCK

    @staticmethod
    def _require_source_reference_id(value: str | None) -> str:
        normalized = normalize_optional_text(value)
        if not normalized:
            raise ValidationError(
                "Maintenance source reference ID is required.",
                code="INVENTORY_MAINTENANCE_SOURCE_REFERENCE_REQUIRED",
            )
        return normalized

    @staticmethod
    def _require_maintenance_enabled(availability: MaintenanceMaterialAvailability) -> None:
        if availability.status != MaintenanceMaterialAvailabilityStatus.NOT_MAINTENANCE_ENABLED:
            return
        raise ValidationError(
            "Selected inventory item category is not enabled for maintenance usage.",
            code="INVENTORY_MAINTENANCE_CATEGORY_FORBIDDEN",
        )

    @staticmethod
    def _emit_material_event(source_reference_type: str, source_reference_id: str) -> None:
        domain_events.inventory_maintenance_materials_changed.emit(f"{source_reference_type}:{source_reference_id}")


__all__ = ["MaintenanceMaterialService"]
