from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.inventory_procurement.domain import (
    StockBalance,
    StockItem,
    StockTransaction,
    StockTransactionType,
    Storeroom,
)
from core.modules.inventory_procurement.interfaces import StockBalanceRepository, StockTransactionRepository
from core.modules.inventory_procurement.services.inventory import InventoryService
from core.modules.inventory_procurement.services.item_master import ItemMasterService
from core.modules.inventory_procurement.support import (
    normalize_nonnegative_quantity,
    normalize_optional_text,
    normalize_positive_quantity,
    normalize_uom,
)
from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository
from core.platform.common.models import Organization
from core.platform.notifications.domain_events import domain_events


def _build_transaction_number() -> str:
    return f"INV-TXN-{uuid4().hex[:10].upper()}"


class StockControlService:
    def __init__(
        self,
        session: Session,
        balance_repo: StockBalanceRepository,
        transaction_repo: StockTransactionRepository,
        *,
        organization_repo: OrganizationRepository,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._balance_repo = balance_repo
        self._transaction_repo = transaction_repo
        self._organization_repo = organization_repo
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._user_session = user_session
        self._audit_service = audit_service

    def list_balances(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
    ) -> list[StockBalance]:
        self._require_read("list stock balances")
        organization = self._active_organization()
        return self._balance_repo.list_for_organization(
            organization.id,
            stock_item_id=normalize_optional_text(stock_item_id) or None,
            storeroom_id=normalize_optional_text(storeroom_id) or None,
        )

    def get_balance(self, balance_id: str) -> StockBalance:
        self._require_read("view stock balance")
        organization = self._active_organization()
        balance = self._balance_repo.get(balance_id)
        if balance is None or balance.organization_id != organization.id:
            raise NotFoundError("Stock balance not found in the active organization.", code="INVENTORY_STOCK_BALANCE_NOT_FOUND")
        return balance

    def get_balance_for_stock_position(self, *, stock_item_id: str, storeroom_id: str) -> StockBalance | None:
        self._require_read("resolve stock balance")
        organization = self._active_organization()
        item = self._item_service.get_item(stock_item_id)
        storeroom = self._inventory_service.get_storeroom(storeroom_id)
        self._ensure_same_scope(item, storeroom, organization)
        return self._balance_repo.get_for_stock_position(organization.id, item.id, storeroom.id)

    def list_transactions(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        limit: int = 200,
    ) -> list[StockTransaction]:
        self._require_read("list stock transactions")
        organization = self._active_organization()
        return self._transaction_repo.list_for_organization(
            organization.id,
            stock_item_id=normalize_optional_text(stock_item_id) or None,
            storeroom_id=normalize_optional_text(storeroom_id) or None,
            limit=max(1, int(limit or 200)),
        )

    def post_opening_balance(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        unit_cost: float = 0.0,
        transaction_at: datetime | None = None,
        notes: str = "",
        commit: bool = True,
    ) -> StockTransaction:
        self._require_manage("post opening balance")
        organization = self._active_organization()
        item = self._validate_stock_item(stock_item_id)
        storeroom = self._validate_storeroom(storeroom_id)
        self._ensure_same_scope(item, storeroom, organization)
        existing_transactions = self._transaction_repo.list_for_organization(
            organization.id,
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            limit=1,
        )
        if existing_transactions:
            raise ValidationError(
                "Opening balance has already been posted for this stock position.",
                code="INVENTORY_OPENING_BALANCE_EXISTS",
            )
        return self._post_transaction(
            organization=organization,
            item=item,
            storeroom=storeroom,
            transaction_type=StockTransactionType.OPENING_BALANCE,
            quantity=quantity,
            uom=uom,
            unit_cost=unit_cost,
            transaction_at=transaction_at,
            reference_type="opening_balance",
            notes=notes,
            commit=commit,
        )

    def post_adjustment(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        direction: str,
        uom: str | None = None,
        unit_cost: float = 0.0,
        transaction_at: datetime | None = None,
        reference_type: str = "adjustment",
        reference_id: str = "",
        notes: str = "",
        commit: bool = True,
    ) -> StockTransaction:
        self._require_manage("post stock adjustment")
        organization = self._active_organization()
        item = self._validate_stock_item(stock_item_id)
        storeroom = self._validate_storeroom(storeroom_id)
        self._ensure_same_scope(item, storeroom, organization)
        normalized_direction = normalize_optional_text(direction).upper()
        if normalized_direction not in {"INCREASE", "DECREASE"}:
            raise ValidationError("Adjustment direction is invalid.", code="INVENTORY_ADJUSTMENT_DIRECTION_INVALID")
        transaction_type = (
            StockTransactionType.ADJUSTMENT_INCREASE
            if normalized_direction == "INCREASE"
            else StockTransactionType.ADJUSTMENT_DECREASE
        )
        return self._post_transaction(
            organization=organization,
            item=item,
            storeroom=storeroom,
            transaction_type=transaction_type,
            quantity=quantity,
            uom=uom,
            unit_cost=unit_cost,
            transaction_at=transaction_at,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            commit=commit,
        )

    def hold_reservation(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        transaction_at: datetime | None = None,
        reference_type: str = "inventory_reservation",
        reference_id: str = "",
        notes: str = "",
        commit: bool = True,
    ) -> StockTransaction:
        self._require_manage("hold stock reservation")
        organization = self._active_organization()
        item = self._validate_stock_item(stock_item_id)
        storeroom = self._validate_storeroom(storeroom_id)
        self._ensure_same_scope(item, storeroom, organization)
        return self._post_reservation_transaction(
            organization=organization,
            item=item,
            storeroom=storeroom,
            quantity=quantity,
            uom=uom,
            transaction_at=transaction_at,
            transaction_type=StockTransactionType.RESERVATION_HOLD,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            commit=commit,
        )

    def release_reservation(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        transaction_at: datetime | None = None,
        reference_type: str = "inventory_reservation",
        reference_id: str = "",
        notes: str = "",
        commit: bool = True,
    ) -> StockTransaction:
        self._require_manage("release stock reservation")
        organization = self._active_organization()
        item = self._validate_stock_item(stock_item_id)
        storeroom = self._validate_storeroom(storeroom_id)
        self._ensure_same_scope(item, storeroom, organization)
        return self._post_reservation_transaction(
            organization=organization,
            item=item,
            storeroom=storeroom,
            quantity=quantity,
            uom=uom,
            transaction_at=transaction_at,
            transaction_type=StockTransactionType.RESERVATION_RELEASE,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            commit=commit,
        )

    def issue_stock(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        unit_cost: float | None = None,
        transaction_at: datetime | None = None,
        release_reserved_qty: float = 0.0,
        reference_type: str = "issue",
        reference_id: str = "",
        notes: str = "",
        commit: bool = True,
    ) -> StockTransaction:
        self._require_manage("issue stock")
        organization = self._active_organization()
        item = self._validate_stock_item(stock_item_id)
        storeroom = self._validate_storeroom(storeroom_id)
        self._ensure_same_scope(item, storeroom, organization)
        return self._post_movement_transaction(
            organization=organization,
            item=item,
            storeroom=storeroom,
            transaction_type=StockTransactionType.ISSUE,
            quantity=quantity,
            uom=uom,
            unit_cost=unit_cost,
            transaction_at=transaction_at,
            release_reserved_qty=release_reserved_qty,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            commit=commit,
        )

    def return_stock(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        unit_cost: float | None = None,
        transaction_at: datetime | None = None,
        reference_type: str = "return",
        reference_id: str = "",
        notes: str = "",
        commit: bool = True,
    ) -> StockTransaction:
        self._require_manage("return stock")
        organization = self._active_organization()
        item = self._validate_stock_item(stock_item_id)
        storeroom = self._validate_storeroom(storeroom_id)
        self._ensure_same_scope(item, storeroom, organization)
        return self._post_movement_transaction(
            organization=organization,
            item=item,
            storeroom=storeroom,
            transaction_type=StockTransactionType.RETURN,
            quantity=quantity,
            uom=uom,
            unit_cost=unit_cost,
            transaction_at=transaction_at,
            release_reserved_qty=0.0,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            commit=commit,
        )

    def transfer_stock(
        self,
        *,
        stock_item_id: str,
        source_storeroom_id: str,
        destination_storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        transaction_at: datetime | None = None,
        notes: str = "",
    ) -> tuple[StockTransaction, StockTransaction]:
        self._require_manage("transfer stock")
        organization = self._active_organization()
        item = self._validate_stock_item(stock_item_id)
        source = self._validate_storeroom(source_storeroom_id)
        destination = self._validate_storeroom(destination_storeroom_id)
        self._ensure_same_scope(item, source, organization)
        self._ensure_same_scope(item, destination, organization)
        if source.id == destination.id:
            raise ValidationError("Source and destination storerooms must be different.", code="INVENTORY_TRANSFER_STOREROOM_DUPLICATE")
        if not source.allows_transfer or not destination.allows_transfer:
            raise ValidationError("Both storerooms must allow transfers.", code="INVENTORY_TRANSFER_FORBIDDEN")
        effective_at = transaction_at or datetime.now(timezone.utc)
        transfer_reference = f"INV-TRF-{uuid4().hex[:10].upper()}"
        try:
            outbound = self._post_movement_transaction(
                organization=organization,
                item=item,
                storeroom=source,
                transaction_type=StockTransactionType.TRANSFER_OUT,
                quantity=quantity,
                uom=uom,
                unit_cost=None,
                transaction_at=effective_at,
                release_reserved_qty=0.0,
                reference_type="stock_transfer",
                reference_id=transfer_reference,
                notes=notes,
                commit=False,
            )
            inbound = self._post_movement_transaction(
                organization=organization,
                item=item,
                storeroom=destination,
                transaction_type=StockTransactionType.TRANSFER_IN,
                quantity=quantity,
                uom=uom,
                unit_cost=outbound.unit_cost,
                transaction_at=effective_at,
                release_reserved_qty=0.0,
                reference_type="stock_transfer",
                reference_id=transfer_reference,
                notes=notes,
                commit=False,
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._record_transaction_audit(item.id, source.id, outbound)
        self._record_transaction_audit(item.id, destination.id, inbound)
        source_balance = self._balance_repo.get_for_stock_position(organization.id, item.id, source.id)
        destination_balance = self._balance_repo.get_for_stock_position(organization.id, item.id, destination.id)
        if source_balance is not None:
            domain_events.inventory_balances_changed.emit(source_balance.id)
        if destination_balance is not None:
            domain_events.inventory_balances_changed.emit(destination_balance.id)
        return outbound, inbound

    def _post_transaction(
        self,
        *,
        organization: Organization,
        item: StockItem,
        storeroom: Storeroom,
        transaction_type: StockTransactionType,
        quantity: float,
        uom: str | None,
        unit_cost: float,
        transaction_at: datetime | None,
        reference_type: str = "",
        reference_id: str = "",
        notes: str = "",
        commit: bool = True,
    ) -> StockTransaction:
        normalized_quantity = normalize_positive_quantity(quantity, label="Transaction quantity")
        normalized_uom = normalize_uom(uom or item.stock_uom, label="Transaction UOM")
        if normalized_uom != item.stock_uom:
            raise ValidationError(
                "Phase-1 stock transactions must use the item's stock UOM.",
                code="INVENTORY_UOM_CONVERSION_REQUIRED",
            )
        normalized_unit_cost = normalize_nonnegative_quantity(unit_cost, label="Unit cost")
        effective_at = transaction_at or datetime.now(timezone.utc)
        balance = self._balance_repo.get_for_stock_position(organization.id, item.id, storeroom.id)
        is_new_balance = balance is None
        if balance is None:
            balance = StockBalance.create(
                organization_id=organization.id,
                stock_item_id=item.id,
                storeroom_id=storeroom.id,
                uom=item.stock_uom,
            )
        previous_on_hand = float(balance.on_hand_qty or 0.0)
        previous_reserved = float(balance.reserved_qty or 0.0)
        delta = self._resolve_quantity_delta(transaction_type, normalized_quantity)
        new_on_hand = previous_on_hand + delta
        if new_on_hand < 0:
            raise ValidationError(
                "Transaction would make on-hand quantity negative.",
                code="INVENTORY_NEGATIVE_ON_HAND",
            )
        if new_on_hand < previous_reserved:
            raise ValidationError(
                "Transaction would make available quantity negative.",
                code="INVENTORY_NEGATIVE_AVAILABLE",
            )
        balance.on_hand_qty = new_on_hand
        balance.available_qty = max(0.0, new_on_hand - previous_reserved)
        balance.uom = item.stock_uom
        balance.average_cost = self._resolve_average_cost(
            balance=balance,
            previous_on_hand=previous_on_hand,
            delta=delta,
            quantity=normalized_quantity,
            unit_cost=normalized_unit_cost,
        )
        if delta > 0:
            balance.last_receipt_at = effective_at
        else:
            balance.last_issue_at = effective_at
        balance.reorder_required = bool(item.reorder_point and balance.available_qty <= float(item.reorder_point or 0.0))
        balance.updated_at = effective_at
        principal = self._user_session.principal if self._user_session is not None else None
        transaction = StockTransaction.create(
            organization_id=organization.id,
            transaction_number=_build_transaction_number(),
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            transaction_type=transaction_type,
            quantity=normalized_quantity,
            uom=normalized_uom,
            unit_cost=normalized_unit_cost,
            transaction_at=effective_at,
            reference_type=normalize_optional_text(reference_type),
            reference_id=normalize_optional_text(reference_id),
            performed_by_user_id=getattr(principal, "user_id", None),
            performed_by_username=str(getattr(principal, "username", "") or ""),
            resulting_on_hand_qty=balance.on_hand_qty,
            resulting_available_qty=balance.available_qty,
            notes=normalize_optional_text(notes),
        )
        try:
            if is_new_balance:
                self._balance_repo.add(balance)
            else:
                self._balance_repo.update(balance)
            self._transaction_repo.add(transaction)
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Stock transaction number already exists.", code="INVENTORY_TRANSACTION_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        if commit:
            record_audit(
                self,
                action="inventory_stock_transaction.post",
                entity_type="inventory_stock_transaction",
                entity_id=transaction.id,
                details={
                    "transaction_number": transaction.transaction_number,
                    "stock_item_id": item.id,
                    "storeroom_id": storeroom.id,
                    "transaction_type": transaction.transaction_type.value,
                    "quantity": str(transaction.quantity),
                    "uom": transaction.uom,
                    "resulting_on_hand_qty": str(transaction.resulting_on_hand_qty),
                    "resulting_available_qty": str(transaction.resulting_available_qty),
                },
            )
            domain_events.inventory_balances_changed.emit(balance.id)
        return transaction

    def _post_reservation_transaction(
        self,
        *,
        organization: Organization,
        item: StockItem,
        storeroom: Storeroom,
        quantity: float,
        uom: str | None,
        transaction_at: datetime | None,
        transaction_type: StockTransactionType,
        reference_type: str = "",
        reference_id: str = "",
        notes: str = "",
        commit: bool = True,
    ) -> StockTransaction:
        normalized_quantity = normalize_positive_quantity(quantity, label="Reservation quantity")
        normalized_uom = normalize_uom(uom or item.stock_uom, label="Reservation UOM")
        if normalized_uom != item.stock_uom:
            raise ValidationError(
                "Phase-1 reservation transactions must use the item's stock UOM.",
                code="INVENTORY_UOM_CONVERSION_REQUIRED",
            )
        effective_at = transaction_at or datetime.now(timezone.utc)
        balance = self._balance_repo.get_for_stock_position(organization.id, item.id, storeroom.id)
        if balance is None:
            raise ValidationError(
                "Stock reservation requires an existing stock balance with available quantity.",
                code="INVENTORY_STOCK_BALANCE_REQUIRED",
            )
        previous_reserved = float(balance.reserved_qty or 0.0)
        previous_on_hand = float(balance.on_hand_qty or 0.0)
        delta = normalized_quantity if transaction_type == StockTransactionType.RESERVATION_HOLD else -normalized_quantity
        new_reserved = previous_reserved + delta
        if new_reserved < 0:
            raise ValidationError(
                "Reservation release would make reserved quantity negative.",
                code="INVENTORY_NEGATIVE_RESERVED",
            )
        new_available = previous_on_hand - new_reserved
        if new_available < 0:
            raise ValidationError(
                "Reservation would make available quantity negative.",
                code="INVENTORY_NEGATIVE_AVAILABLE",
            )
        balance.reserved_qty = new_reserved
        balance.available_qty = new_available
        balance.uom = item.stock_uom
        balance.reorder_required = bool(item.reorder_point and balance.available_qty <= float(item.reorder_point or 0.0))
        balance.updated_at = effective_at
        principal = self._user_session.principal if self._user_session is not None else None
        transaction = StockTransaction.create(
            organization_id=organization.id,
            transaction_number=_build_transaction_number(),
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            transaction_type=transaction_type,
            quantity=normalized_quantity,
            uom=normalized_uom,
            unit_cost=0.0,
            transaction_at=effective_at,
            reference_type=normalize_optional_text(reference_type),
            reference_id=normalize_optional_text(reference_id),
            performed_by_user_id=getattr(principal, "user_id", None),
            performed_by_username=str(getattr(principal, "username", "") or ""),
            resulting_on_hand_qty=balance.on_hand_qty,
            resulting_available_qty=balance.available_qty,
            notes=normalize_optional_text(notes),
        )
        try:
            self._balance_repo.update(balance)
            self._transaction_repo.add(transaction)
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Stock transaction number already exists.", code="INVENTORY_TRANSACTION_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        if commit:
            record_audit(
                self,
                action="inventory_stock_transaction.post",
                entity_type="inventory_stock_transaction",
                entity_id=transaction.id,
                details={
                    "transaction_number": transaction.transaction_number,
                    "stock_item_id": item.id,
                    "storeroom_id": storeroom.id,
                    "transaction_type": transaction.transaction_type.value,
                    "quantity": str(transaction.quantity),
                    "uom": transaction.uom,
                    "resulting_on_hand_qty": str(transaction.resulting_on_hand_qty),
                    "resulting_available_qty": str(transaction.resulting_available_qty),
                },
            )
            domain_events.inventory_balances_changed.emit(balance.id)
        return transaction

    def _post_movement_transaction(
        self,
        *,
        organization: Organization,
        item: StockItem,
        storeroom: Storeroom,
        transaction_type: StockTransactionType,
        quantity: float,
        uom: str | None,
        unit_cost: float | None,
        transaction_at: datetime | None,
        release_reserved_qty: float,
        reference_type: str = "",
        reference_id: str = "",
        notes: str = "",
        commit: bool = True,
    ) -> StockTransaction:
        normalized_quantity = normalize_positive_quantity(quantity, label="Movement quantity")
        normalized_reserved_release = normalize_nonnegative_quantity(release_reserved_qty, label="Reserved release quantity")
        if normalized_reserved_release > normalized_quantity:
            raise ValidationError(
                "Reserved release quantity cannot exceed issued quantity.",
                code="INVENTORY_RESERVED_RELEASE_INVALID",
            )
        normalized_uom = normalize_uom(uom or item.stock_uom, label="Movement UOM")
        if normalized_uom != item.stock_uom:
            raise ValidationError(
                "Phase-1 stock movements must use the item's stock UOM.",
                code="INVENTORY_UOM_CONVERSION_REQUIRED",
            )
        effective_at = transaction_at or datetime.now(timezone.utc)
        balance = self._balance_repo.get_for_stock_position(organization.id, item.id, storeroom.id)
        is_new_balance = balance is None
        if balance is None:
            if transaction_type not in {StockTransactionType.RETURN, StockTransactionType.TRANSFER_IN}:
                raise ValidationError(
                    "Stock movement requires an existing stock balance.",
                    code="INVENTORY_STOCK_BALANCE_REQUIRED",
                )
            balance = StockBalance.create(
                organization_id=organization.id,
                stock_item_id=item.id,
                storeroom_id=storeroom.id,
                uom=item.stock_uom,
            )
        previous_on_hand = float(balance.on_hand_qty or 0.0)
        previous_reserved = float(balance.reserved_qty or 0.0)
        on_hand_delta = normalized_quantity if transaction_type in {StockTransactionType.RETURN, StockTransactionType.TRANSFER_IN} else -normalized_quantity
        reserved_delta = -normalized_reserved_release
        new_on_hand = previous_on_hand + on_hand_delta
        new_reserved = previous_reserved + reserved_delta
        if new_on_hand < 0:
            raise ValidationError(
                "Movement would make on-hand quantity negative.",
                code="INVENTORY_NEGATIVE_ON_HAND",
            )
        if new_reserved < 0:
            raise ValidationError(
                "Movement would make reserved quantity negative.",
                code="INVENTORY_NEGATIVE_RESERVED",
            )
        new_available = new_on_hand - new_reserved
        if new_available < 0:
            raise ValidationError(
                "Movement would make available quantity negative.",
                code="INVENTORY_NEGATIVE_AVAILABLE",
            )
        effective_unit_cost = (
            normalize_nonnegative_quantity(unit_cost, label="Unit cost")
            if unit_cost is not None
            else float(balance.average_cost or 0.0)
        )
        balance.on_hand_qty = new_on_hand
        balance.reserved_qty = new_reserved
        balance.available_qty = new_available
        balance.uom = item.stock_uom
        if on_hand_delta > 0:
            balance.last_receipt_at = effective_at
            balance.average_cost = self._resolve_average_cost(
                balance=balance,
                previous_on_hand=previous_on_hand,
                delta=on_hand_delta,
                quantity=normalized_quantity,
                unit_cost=effective_unit_cost,
            )
        else:
            balance.last_issue_at = effective_at
        balance.reorder_required = bool(item.reorder_point and balance.available_qty <= float(item.reorder_point or 0.0))
        balance.updated_at = effective_at
        principal = self._user_session.principal if self._user_session is not None else None
        transaction = StockTransaction.create(
            organization_id=organization.id,
            transaction_number=_build_transaction_number(),
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            transaction_type=transaction_type,
            quantity=normalized_quantity,
            uom=normalized_uom,
            unit_cost=effective_unit_cost,
            transaction_at=effective_at,
            reference_type=normalize_optional_text(reference_type),
            reference_id=normalize_optional_text(reference_id),
            performed_by_user_id=getattr(principal, "user_id", None),
            performed_by_username=str(getattr(principal, "username", "") or ""),
            resulting_on_hand_qty=balance.on_hand_qty,
            resulting_available_qty=balance.available_qty,
            notes=normalize_optional_text(notes),
        )
        try:
            if is_new_balance:
                self._balance_repo.add(balance)
            else:
                self._balance_repo.update(balance)
            self._transaction_repo.add(transaction)
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Stock transaction number already exists.", code="INVENTORY_TRANSACTION_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        if commit:
            self._record_transaction_audit(item.id, storeroom.id, transaction)
            domain_events.inventory_balances_changed.emit(balance.id)
        return transaction

    def _resolve_average_cost(
        self,
        *,
        balance: StockBalance,
        previous_on_hand: float,
        delta: float,
        quantity: float,
        unit_cost: float,
    ) -> float:
        if delta <= 0:
            return float(balance.average_cost or 0.0)
        if previous_on_hand <= 0:
            return unit_cost
        previous_average = float(balance.average_cost or 0.0)
        new_on_hand = float(balance.on_hand_qty or 0.0)
        if new_on_hand <= 0:
            return unit_cost
        return ((previous_on_hand * previous_average) + (quantity * unit_cost)) / new_on_hand

    def _resolve_quantity_delta(self, transaction_type: StockTransactionType, quantity: float) -> float:
        if transaction_type in {
            StockTransactionType.OPENING_BALANCE,
            StockTransactionType.ADJUSTMENT_INCREASE,
            StockTransactionType.RETURN,
            StockTransactionType.TRANSFER_IN,
        }:
            return quantity
        return -quantity

    def _record_transaction_audit(self, stock_item_id: str, storeroom_id: str, transaction: StockTransaction) -> None:
        record_audit(
            self,
            action="inventory_stock_transaction.post",
            entity_type="inventory_stock_transaction",
            entity_id=transaction.id,
            details={
                "transaction_number": transaction.transaction_number,
                "stock_item_id": stock_item_id,
                "storeroom_id": storeroom_id,
                "transaction_type": transaction.transaction_type.value,
                "quantity": str(transaction.quantity),
                "uom": transaction.uom,
                "resulting_on_hand_qty": str(transaction.resulting_on_hand_qty),
                "resulting_available_qty": str(transaction.resulting_available_qty),
            },
        )

    def _validate_stock_item(self, stock_item_id: str) -> StockItem:
        item = self._item_service.get_item(stock_item_id)
        if not item.is_active:
            raise ValidationError("Stock item must be active before transactions can be posted.", code="INVENTORY_ITEM_INACTIVE")
        if not item.is_stocked:
            raise ValidationError("Non-stocked items cannot receive stock transactions.", code="INVENTORY_ITEM_NOT_STOCKED")
        return item

    def _validate_storeroom(self, storeroom_id: str) -> Storeroom:
        storeroom = self._inventory_service.get_storeroom(storeroom_id)
        if not storeroom.is_active:
            raise ValidationError("Storeroom must be active before transactions can be posted.", code="INVENTORY_STOREROOM_INACTIVE")
        return storeroom

    def _ensure_same_scope(self, item: StockItem, storeroom: Storeroom, organization: Organization) -> None:
        if item.organization_id != organization.id or storeroom.organization_id != organization.id:
            raise ValidationError(
                "Stock transaction references must stay inside the active organization.",
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


__all__ = ["StockControlService"]
