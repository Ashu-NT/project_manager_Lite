from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.inventory_procurement.domain import StockReservation, StockReservationStatus
from core.modules.inventory_procurement.interfaces import StockReservationRepository
from core.modules.inventory_procurement.services.inventory import InventoryService
from core.modules.inventory_procurement.services.item_master import ItemMasterService
from core.modules.inventory_procurement.services.stock_control import StockControlService
from core.modules.inventory_procurement.support import (
    RESERVATION_STATUS_TRANSITIONS,
    normalize_optional_text,
    normalize_positive_quantity,
    normalize_source_reference_type,
    normalize_uom,
    resolve_item_uom_factor,
    validate_transition,
)
from src.core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.org.domain import Organization
from src.core.platform.notifications.domain_events import domain_events


def _build_reservation_number() -> str:
    return f"INV-RES-{uuid4().hex[:10].upper()}"


class ReservationService:
    def __init__(
        self,
        session: Session,
        reservation_repo: StockReservationRepository,
        *,
        organization_repo: OrganizationRepository,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        stock_service: StockControlService,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._reservation_repo = reservation_repo
        self._organization_repo = organization_repo
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._stock_service = stock_service
        self._user_session = user_session
        self._audit_service = audit_service

    def list_reservations(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[StockReservation]:
        self._require_read("list stock reservations")
        organization = self._active_organization()
        return self._reservation_repo.list_for_organization(
            organization.id,
            stock_item_id=normalize_optional_text(stock_item_id) or None,
            storeroom_id=normalize_optional_text(storeroom_id) or None,
            status=normalize_optional_text(status).upper() or None,
            limit=max(1, int(limit or 200)),
        )

    def get_reservation(self, reservation_id: str) -> StockReservation:
        self._require_read("view stock reservation")
        organization = self._active_organization()
        reservation = self._reservation_repo.get(reservation_id)
        if reservation is None or reservation.organization_id != organization.id:
            raise NotFoundError(
                "Stock reservation not found in the active organization.",
                code="INVENTORY_RESERVATION_NOT_FOUND",
            )
        return reservation

    def create_reservation(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        reserved_qty: float,
        uom: str | None = None,
        need_by_date: date | None = None,
        source_reference_type: str,
        source_reference_id: str,
        notes: str = "",
    ) -> StockReservation:
        self._require_manage("create stock reservation")
        organization = self._active_organization()
        item = self._item_service.get_item(stock_item_id)
        storeroom = self._inventory_service.get_storeroom(storeroom_id)
        self._ensure_same_scope(item.organization_id, storeroom.organization_id, organization.id)
        if not item.is_active or not item.is_stocked:
            raise ValidationError("Reservation item must be an active stocked item.", code="INVENTORY_ITEM_NOT_STOCKED")
        if not storeroom.is_active:
            raise ValidationError("Reservation storeroom must be active.", code="INVENTORY_STOREROOM_INACTIVE")
        normalized_source_type = normalize_source_reference_type(source_reference_type)
        normalized_source_id = normalize_optional_text(source_reference_id)
        if not normalized_source_type or not normalized_source_id:
            raise ValidationError(
                "Stock reservation requires source reference type and ID.",
                code="INVENTORY_RESERVATION_SOURCE_REQUIRED",
            )
        normalized_qty = normalize_positive_quantity(reserved_qty, label="Reservation quantity")
        normalized_uom = normalize_uom(uom or item.stock_uom, label="Reservation UOM")
        resolve_item_uom_factor(item, normalized_uom, label="Reservation UOM")
        principal = self._user_session.principal if self._user_session is not None else None
        reservation = StockReservation.create(
            organization_id=organization.id,
            reservation_number=_build_reservation_number(),
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            reserved_qty=normalized_qty,
            remaining_qty=normalized_qty,
            uom=normalized_uom,
            need_by_date=need_by_date,
            source_reference_type=normalized_source_type,
            source_reference_id=normalized_source_id,
            requested_by_user_id=getattr(principal, "user_id", None),
            requested_by_username=str(getattr(principal, "username", "") or ""),
            notes=normalize_optional_text(notes),
        )
        try:
            self._reservation_repo.add(reservation)
            transaction = self._stock_service.hold_reservation(
                stock_item_id=item.id,
                storeroom_id=storeroom.id,
                quantity=normalized_qty,
                uom=normalized_uom,
                reference_type="inventory_reservation",
                reference_id=reservation.id,
                notes=reservation.notes,
                commit=False,
            )
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Reservation number already exists.", code="INVENTORY_RESERVATION_NUMBER_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_reservation.create",
            entity_type="stock_reservation",
            entity_id=reservation.id,
            details={
                "reservation_number": reservation.reservation_number,
                "stock_item_id": reservation.stock_item_id,
                "storeroom_id": reservation.storeroom_id,
                "reserved_qty": str(reservation.reserved_qty),
                "source_reference_type": reservation.source_reference_type,
                "source_reference_id": reservation.source_reference_id,
            },
        )
        self._record_transaction_audit(transaction)
        balance = self._stock_service.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=storeroom.id)
        if balance is not None:
            domain_events.inventory_balances_changed.emit(balance.id)
        domain_events.inventory_reservations_changed.emit(reservation.id)
        return reservation

    def release_reservation(self, reservation_id: str, *, note: str = "") -> StockReservation:
        self._require_manage("release stock reservation")
        reservation = self.get_reservation(reservation_id)
        return self._close_reservation(reservation, status=StockReservationStatus.RELEASED, note=note)

    def cancel_reservation(self, reservation_id: str, *, note: str = "") -> StockReservation:
        self._require_manage("cancel stock reservation")
        reservation = self.get_reservation(reservation_id)
        return self._close_reservation(reservation, status=StockReservationStatus.CANCELLED, note=note)

    def issue_reserved_stock(
        self,
        reservation_id: str,
        *,
        quantity: float,
        note: str = "",
    ) -> StockReservation:
        self._require_manage("issue reserved stock")
        reservation = self.get_reservation(reservation_id)
        if reservation.status not in {StockReservationStatus.ACTIVE, StockReservationStatus.PARTIALLY_ISSUED}:
            raise ValidationError(
                "Only active reservations can be issued.",
                code="INVENTORY_RESERVATION_STATUS_INVALID",
            )
        issue_qty = normalize_positive_quantity(quantity, label="Issued quantity")
        if issue_qty > float(reservation.remaining_qty or 0.0):
            raise ValidationError(
                "Issued quantity exceeds the reservation remaining quantity.",
                code="INVENTORY_RESERVATION_QTY_EXCEEDED",
            )
        effective_at = datetime.now(timezone.utc)
        next_remaining = max(0.0, float(reservation.remaining_qty or 0.0) - issue_qty)
        next_status = (
            StockReservationStatus.FULLY_ISSUED
            if next_remaining <= 0
            else StockReservationStatus.PARTIALLY_ISSUED
        )
        validate_transition(
            current_status=reservation.status.value,
            next_status=next_status.value,
            transitions=RESERVATION_STATUS_TRANSITIONS,
        )
        try:
            transaction = self._stock_service.issue_stock(
                stock_item_id=reservation.stock_item_id,
                storeroom_id=reservation.storeroom_id,
                quantity=issue_qty,
                uom=reservation.uom,
                transaction_at=effective_at,
                release_reserved_qty=issue_qty,
                reference_type="inventory_reservation",
                reference_id=reservation.id,
                notes=normalize_optional_text(note) or reservation.notes,
                commit=False,
            )
            reservation.issued_qty = float(reservation.issued_qty or 0.0) + issue_qty
            reservation.remaining_qty = next_remaining
            reservation.status = next_status
            reservation.notes = normalize_optional_text(note) or reservation.notes
            self._reservation_repo.update(reservation)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_reservation.issue",
            entity_type="stock_reservation",
            entity_id=reservation.id,
            details={
                "reservation_number": reservation.reservation_number,
                "issued_qty": str(issue_qty),
                "remaining_qty": str(reservation.remaining_qty),
            },
        )
        self._record_transaction_audit(transaction)
        balance = self._stock_service.get_balance_for_stock_position(
            stock_item_id=reservation.stock_item_id,
            storeroom_id=reservation.storeroom_id,
        )
        if balance is not None:
            domain_events.inventory_balances_changed.emit(balance.id)
        domain_events.inventory_reservations_changed.emit(reservation.id)
        return reservation

    def _close_reservation(
        self,
        reservation: StockReservation,
        *,
        status: StockReservationStatus,
        note: str,
    ) -> StockReservation:
        if reservation.status not in {StockReservationStatus.ACTIVE, StockReservationStatus.PARTIALLY_ISSUED}:
            raise ValidationError(
                "Only active reservations can be closed.",
                code="INVENTORY_RESERVATION_STATUS_INVALID",
            )
        quantity_to_release = float(reservation.remaining_qty or 0.0)
        if quantity_to_release <= 0:
            raise ValidationError(
                "Reservation has no remaining quantity to release.",
                code="INVENTORY_RESERVATION_ALREADY_CONSUMED",
            )
        effective_at = datetime.now(timezone.utc)
        validate_transition(
            current_status=reservation.status.value,
            next_status=status.value,
            transitions=RESERVATION_STATUS_TRANSITIONS,
        )
        try:
            transaction = self._stock_service.release_reservation(
                stock_item_id=reservation.stock_item_id,
                storeroom_id=reservation.storeroom_id,
                quantity=quantity_to_release,
                uom=reservation.uom,
                transaction_at=effective_at,
                reference_type="inventory_reservation",
                reference_id=reservation.id,
                notes=normalize_optional_text(note) or reservation.notes,
                commit=False,
            )
            reservation.remaining_qty = 0.0
            if status == StockReservationStatus.RELEASED:
                reservation.released_at = effective_at
            else:
                reservation.cancelled_at = effective_at
            reservation.status = status
            reservation.notes = normalize_optional_text(note) or reservation.notes
            self._reservation_repo.update(reservation)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action=f"inventory_reservation.{status.value.lower()}",
            entity_type="stock_reservation",
            entity_id=reservation.id,
            details={
                "reservation_number": reservation.reservation_number,
                "released_qty": str(quantity_to_release),
            },
        )
        self._record_transaction_audit(transaction)
        balance = self._stock_service.get_balance_for_stock_position(
            stock_item_id=reservation.stock_item_id,
            storeroom_id=reservation.storeroom_id,
        )
        if balance is not None:
            domain_events.inventory_balances_changed.emit(balance.id)
        domain_events.inventory_reservations_changed.emit(reservation.id)
        return reservation

    def _record_transaction_audit(self, transaction) -> None:
        record_audit(
            self,
            action="inventory_stock_transaction.post",
            entity_type="inventory_stock_transaction",
            entity_id=transaction.id,
            details={
                "transaction_number": transaction.transaction_number,
                "stock_item_id": transaction.stock_item_id,
                "storeroom_id": transaction.storeroom_id,
                "transaction_type": transaction.transaction_type.value,
                "quantity": str(transaction.quantity),
                "uom": transaction.uom,
                "reference_id": transaction.reference_id,
            },
        )

    @staticmethod
    def _ensure_same_scope(item_org_id: str, storeroom_org_id: str, organization_id: str) -> None:
        if item_org_id != organization_id or storeroom_org_id != organization_id:
            raise ValidationError(
                "Reservation references must stay inside the active organization.",
                code="INVENTORY_SCOPE_INVALID",
            )

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.manage", operation_label=operation_label)


__all__ = ["ReservationService"]
