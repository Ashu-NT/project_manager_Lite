from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.common.support import (
    RESERVATION_STATUS_TRANSITIONS,
    normalize_optional_text,
    normalize_positive_quantity,
    resolve_item_uom_factor,
    validate_transition,
)
from src.core.modules.inventory_procurement.application.inventory.service import InventoryService
from src.core.modules.inventory_procurement.application.inventory.stock_control_service import (
    StockControlService,
)
from src.core.modules.inventory_procurement.contracts.persistence.reservation_unit_of_work import (
    InventoryReservationUnitOfWorkFactory,
)
from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    StockReservationRepository,
)
from src.core.modules.inventory_procurement.domain.inventory.reservation_events import (
    InventoryReservationCancelled,
    InventoryReservationConsumptionAdvanced,
    InventoryReservationCreated,
    InventoryReservationReleased,
)
from src.core.modules.inventory_procurement.domain.inventory.stock import (
    StockReservation,
    StockReservationStatus,
)
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.application.master_data.documents import DocumentIntegrationService
from src.core.platform.domain.master_data.documents import Document, DocumentLink
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)


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
        reservation_uow_factory: InventoryReservationUnitOfWorkFactory | None = None,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
        document_integration_service: DocumentIntegrationService | None = None,
    ):
        self._session = session
        self._reservation_repo = reservation_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="ReservationService",
        )
        self._item_service = item_service
        self._inventory_service = inventory_service
        # Retained only for the post-commit legacy `inventory_balances_changed` read -- Balance
        # is explicitly out of scope for modernization here (P30B). All Reservation-owned
        # mutations go through `_reservation_uow_factory` / `uow.stock_service` instead.
        self._stock_service = stock_service
        self._reservation_uow_factory = reservation_uow_factory
        self._user_session = user_session
        self._activity_service = activity_service
        self._document_integration_service = document_integration_service

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
        source_module: str = "",
        source_entity_type: str = "",
        source_code_snapshot: str = "",
        source_title_snapshot: str = "",
        source_status_snapshot: str = "",
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
        principal = self._user_session.principal if self._user_session is not None else None
        reservation = StockReservation.create(
            organization_id=organization.id,
            reservation_number=_build_reservation_number(),
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            reserved_qty=reserved_qty,
            remaining_qty=reserved_qty,
            uom=uom or item.stock_uom,
            need_by_date=need_by_date,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            source_module=source_module or "",
            source_entity_type=source_entity_type or "",
            source_code_snapshot=source_code_snapshot or "",
            source_title_snapshot=source_title_snapshot or "",
            source_status_snapshot=source_status_snapshot or "",
            requested_by_user_id=getattr(principal, "user_id", None),
            requested_by_username=str(getattr(principal, "username", "") or ""),
            notes=notes,
        )
        resolve_item_uom_factor(item, reservation.uom, label="Reservation UOM")
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="create stock reservation"
        )
        occurred_at = datetime.now(timezone.utc)
        try:
            with self._require_reservation_uow_factory().create(
                context=DomainEventContext(correlation_id=generate_id())
            ) as uow:
                uow.reservations.add(reservation)
                transaction = uow.stock_service.hold_reservation(
                    stock_item_id=item.id,
                    storeroom_id=storeroom.id,
                    quantity=reservation.reserved_qty,
                    uom=reservation.uom,
                    reference_type="inventory_reservation",
                    reference_id=reservation.id,
                    notes=reservation.notes,
                    commit=False,
                )
                record_activity(
                    uow,
                    action="inventory_reservation.create",
                    entity_type="stock_reservation",
                    entity_id=reservation.id,
                    module="inventory",
                    details={
                        "reservation_number": reservation.reservation_number,
                        "stock_item_id": reservation.stock_item_id,
                        "storeroom_id": reservation.storeroom_id,
                        "reserved_qty": str(reservation.reserved_qty),
                        "source_reference_type": reservation.source_reference_type,
                        "source_reference_id": reservation.source_reference_id,
                    },
                    commit=False,
                )
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="stock_reservation",
                    entity_id=reservation.id,
                    module="inventory",
                    severity="low",
                    metadata={
                        "reservation_number": reservation.reservation_number,
                        "stock_item_id": reservation.stock_item_id,
                        "storeroom_id": reservation.storeroom_id,
                        "reserved_qty": str(reservation.reserved_qty),
                    },
                    commit=False,
                    fail_closed=True,
                )
                self._record_transaction_audit(uow, transaction)
                uow.record_event(
                    InventoryReservationCreated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        reservation_id=reservation.id,
                        occurred_at=occurred_at,
                    )
                )
                uow.commit()
        except IntegrityError as exc:
            raise ValidationError("Reservation number already exists.", code="INVENTORY_RESERVATION_NUMBER_EXISTS") from exc
        self._emit_legacy_balance_signal(stock_item_id=item.id, storeroom_id=storeroom.id)
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
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="issue reserved stock"
        )
        with self._require_reservation_uow_factory().create(
            context=DomainEventContext(correlation_id=generate_id())
        ) as uow:
            transaction = uow.stock_service.issue_stock(
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
            reservation = replace(
                reservation,
                issued_qty=float(reservation.issued_qty or 0.0) + issue_qty,
                remaining_qty=next_remaining,
                status=next_status,
                notes=normalize_optional_text(note) or reservation.notes,
            )
            uow.reservations.update(reservation)
            record_activity(
                uow,
                action="inventory_reservation.issue",
                entity_type="stock_reservation",
                entity_id=reservation.id,
                module="inventory",
                details={
                    "reservation_number": reservation.reservation_number,
                    "issued_qty": str(issue_qty),
                    "remaining_qty": str(reservation.remaining_qty),
                },
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="stock_reservation",
                entity_id=reservation.id,
                module="inventory",
                severity="low",
                metadata={
                    "reservation_number": reservation.reservation_number,
                    "issued_qty": str(issue_qty),
                    "resulting_status": next_status.value,
                },
                commit=False,
                fail_closed=True,
            )
            self._record_transaction_audit(uow, transaction)
            uow.record_event(
                InventoryReservationConsumptionAdvanced(
                    tenant_id=tenant_id,
                    organization_id=reservation.organization_id,
                    reservation_id=reservation.id,
                    resulting_status=next_status.value,
                    occurred_at=effective_at,
                )
            )
            uow.commit()
        self._emit_legacy_balance_signal(
            stock_item_id=reservation.stock_item_id,
            storeroom_id=reservation.storeroom_id,
        )
        return reservation

    def list_reservation_documents(
        self,
        reservation_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Document]:
        if self._document_integration_service is None:
            return []
        reservation = self.get_reservation(reservation_id)
        return self._document_integration_service.list_documents_for_entity(
            required_permission="inventory.read",
            operation_label="list reservation documents",
            module_code="inventory_procurement",
            entity_type="stock_reservation",
            entity_id=reservation.id,
            module="inventory",
            active_only=active_only,
        )

    def link_document(
        self,
        reservation_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> DocumentLink:
        if self._document_integration_service is None:
            raise ValidationError(
                "Document integration is not available.",
                code="DOCUMENT_INTEGRATION_UNAVAILABLE",
            )
        reservation = self.get_reservation(reservation_id)
        # Document link/unlink mutates only `DocumentLink`, never the Reservation row itself --
        # P30A/P30B: no Reservation DomainEvent, no legacy `inventory_reservations_changed`.
        # `link_existing_document` is already P16D-typed and already drives the canonical
        # `document_links` ViewInvalidation target on its own, atomically -- the identical
        # precedent P24 already established for Item's own link_document/unlink_document.
        link = self._document_integration_service.link_existing_document(
            required_permission="inventory.manage",
            operation_label="link reservation document",
            module_code="inventory_procurement",
            entity_type="stock_reservation",
            entity_id=reservation.id,
            module="inventory",
            document_id=document_id,
            link_role=link_role,
        )
        record_activity(
            self,
            action="inventory_reservation.link_document",
            entity_type="stock_reservation",
            entity_id=reservation.id,
            module="inventory",
            details={
                "document_id": document_id,
                "link_role": normalize_optional_text(link_role) or "reference",
            },
        )
        return link

    def unlink_document(
        self,
        reservation_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> None:
        if self._document_integration_service is None:
            raise ValidationError(
                "Document integration is not available.",
                code="DOCUMENT_INTEGRATION_UNAVAILABLE",
            )
        reservation = self.get_reservation(reservation_id)
        # See `link_document` -- same P16D-owned, already-atomic path, no Reservation event.
        self._document_integration_service.unlink_existing_document(
            required_permission="inventory.manage",
            operation_label="unlink reservation document",
            module_code="inventory_procurement",
            entity_type="stock_reservation",
            entity_id=reservation.id,
            module="inventory",
            document_id=document_id,
            link_role=link_role,
        )
        record_activity(
            self,
            action="inventory_reservation.unlink_document",
            entity_type="stock_reservation",
            entity_id=reservation.id,
            module="inventory",
            details={
                "document_id": document_id,
                "link_role": normalize_optional_text(link_role) or "reference",
            },
        )

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
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="close stock reservation"
        )
        with self._require_reservation_uow_factory().create(
            context=DomainEventContext(correlation_id=generate_id())
        ) as uow:
            transaction = uow.stock_service.release_reservation(
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
            reservation = replace(
                reservation,
                remaining_qty=0.0,
                released_at=(
                    effective_at
                    if status == StockReservationStatus.RELEASED
                    else reservation.released_at
                ),
                cancelled_at=(
                    effective_at
                    if status == StockReservationStatus.CANCELLED
                    else reservation.cancelled_at
                ),
                status=status,
                notes=normalize_optional_text(note) or reservation.notes,
            )
            uow.reservations.update(reservation)
            record_activity(
                uow,
                action=f"inventory_reservation.{status.value.lower()}",
                entity_type="stock_reservation",
                entity_id=reservation.id,
                module="inventory",
                details={
                    "reservation_number": reservation.reservation_number,
                    "released_qty": str(quantity_to_release),
                },
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="stock_reservation",
                entity_id=reservation.id,
                module="inventory",
                severity="low",
                metadata={
                    "reservation_number": reservation.reservation_number,
                    "resulting_status": status.value,
                    "released_qty": str(quantity_to_release),
                },
                commit=False,
                fail_closed=True,
            )
            self._record_transaction_audit(uow, transaction)
            # Released vs Cancelled are kept as distinct DomainEvent types even though they
            # share this one implementation helper -- P30B §4: different terminal business
            # decisions, not an implementation detail to collapse into one `ReservationClosed`.
            if status == StockReservationStatus.RELEASED:
                uow.record_event(
                    InventoryReservationReleased(
                        tenant_id=tenant_id,
                        organization_id=reservation.organization_id,
                        reservation_id=reservation.id,
                        occurred_at=effective_at,
                    )
                )
            else:
                uow.record_event(
                    InventoryReservationCancelled(
                        tenant_id=tenant_id,
                        organization_id=reservation.organization_id,
                        reservation_id=reservation.id,
                        occurred_at=effective_at,
                    )
                )
            uow.commit()
        self._emit_legacy_balance_signal(
            stock_item_id=reservation.stock_item_id,
            storeroom_id=reservation.storeroom_id,
        )
        return reservation

    def _record_transaction_audit(self, uow, transaction) -> None:
        record_activity(
            uow,
            action="inventory_stock_transaction.post",
            entity_type="inventory_stock_transaction",
            entity_id=transaction.id,
            module="inventory",
            details={
                "transaction_number": transaction.transaction_number,
                "stock_item_id": transaction.stock_item_id,
                "storeroom_id": transaction.storeroom_id,
                "transaction_type": transaction.transaction_type.value,
                "quantity": str(transaction.quantity),
                "uom": transaction.uom,
                "reference_id": transaction.reference_id,
            },
            commit=False,
        )

    def _emit_legacy_balance_signal(self, *, stock_item_id: str, storeroom_id: str) -> None:
        # `inventory_balances_changed` is unchanged/retained -- Balance is a separate, still-
        # legacy capability (explicitly out of scope for P30B). Reservation genuinely mutates
        # persisted Balance state (see `uow.stock_service` above), so this notification is a
        # real, correct fact about a different capability, not a compatibility shim for the
        # just-retired `inventory_reservations_changed`.
        balance = self._stock_service.get_balance_for_stock_position(
            stock_item_id=stock_item_id, storeroom_id=storeroom_id
        )
        if balance is not None:
            domain_events.inventory_balances_changed.emit(balance.id)

    def _require_reservation_uow_factory(self) -> InventoryReservationUnitOfWorkFactory:
        if self._reservation_uow_factory is None:
            raise BusinessRuleError(
                "Stock reservation commands require a configured transaction owner.",
                code="INVENTORY_RESERVATION_UOW_REQUIRED",
            )
        return self._reservation_uow_factory

    @staticmethod
    def _ensure_same_scope(item_org_id: str, storeroom_org_id: str, organization_id: str) -> None:
        if item_org_id != organization_id or storeroom_org_id != organization_id:
            raise ValidationError(
                "Reservation references must stay inside the active organization.",
                code="INVENTORY_SCOPE_INVALID",
            )

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="inventory reservations"
        ).organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.manage", operation_label=operation_label)


__all__ = ["ReservationService"]
