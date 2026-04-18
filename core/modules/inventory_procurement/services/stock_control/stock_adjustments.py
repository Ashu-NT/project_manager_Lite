from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from core.modules.inventory_procurement.domain import StockBalance, StockItem, StockTransaction, StockTransactionType, Storeroom
from core.modules.inventory_procurement.services.stock_control.stock_support import build_transaction_number
from core.modules.inventory_procurement.support import (
    convert_item_quantity,
    convert_item_unit_cost_to_stock,
    normalize_nonnegative_quantity,
    normalize_optional_text,
    normalize_positive_quantity,
    normalize_uom,
)
from core.platform.audit.helpers import record_audit
from core.platform.common.exceptions import ValidationError
from src.core.platform.org.domain import Organization
from src.core.platform.notifications.domain_events import domain_events


class StockControlAdjustmentMixin:
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
        stock_quantity = convert_item_quantity(
            item,
            normalized_quantity,
            from_uom=normalized_uom,
            to_uom=item.stock_uom,
            label="Transaction UOM",
        )
        normalized_unit_cost = normalize_nonnegative_quantity(unit_cost, label="Unit cost")
        stock_unit_cost = convert_item_unit_cost_to_stock(
            item,
            normalized_unit_cost,
            uom=normalized_uom,
            label="Unit cost",
        )
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
        delta = self._resolve_quantity_delta(transaction_type, stock_quantity)
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
            quantity=stock_quantity,
            unit_cost=stock_unit_cost,
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
            transaction_number=build_transaction_number(),
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
        stock_quantity = convert_item_quantity(
            item,
            normalized_quantity,
            from_uom=normalized_uom,
            to_uom=item.stock_uom,
            label="Reservation UOM",
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
        delta = stock_quantity if transaction_type == StockTransactionType.RESERVATION_HOLD else -stock_quantity
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
            transaction_number=build_transaction_number(),
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


__all__ = ["StockControlAdjustmentMixin"]
