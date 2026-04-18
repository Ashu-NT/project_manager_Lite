from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

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
    resolve_item_uom_factor,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.org.domain import Organization
from src.core.platform.notifications.domain_events import domain_events


class StockControlMovementMixin:
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
        if not storeroom.allows_issue:
            raise ValidationError("Selected storeroom does not allow issues.", code="INVENTORY_ISSUE_FORBIDDEN")
        if storeroom.requires_reservation_for_issue and float(release_reserved_qty or 0.0) <= 0:
            raise ValidationError(
                "Selected storeroom requires a linked reservation release for issues.",
                code="INVENTORY_ISSUE_RESERVATION_REQUIRED",
            )
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
        normalized_uom = normalize_uom(uom or item.stock_uom, label="Movement UOM")
        movement_stock_quantity = convert_item_quantity(
            item,
            normalized_quantity,
            from_uom=normalized_uom,
            to_uom=item.stock_uom,
            label="Movement UOM",
        )
        reserved_release_stock_quantity = convert_item_quantity(
            item,
            normalized_reserved_release,
            from_uom=normalized_uom,
            to_uom=item.stock_uom,
            label="Movement UOM",
        )
        if reserved_release_stock_quantity > movement_stock_quantity:
            raise ValidationError(
                "Reserved release quantity cannot exceed issued quantity.",
                code="INVENTORY_RESERVED_RELEASE_INVALID",
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
        on_hand_delta = (
            movement_stock_quantity
            if transaction_type in {StockTransactionType.RETURN, StockTransactionType.TRANSFER_IN}
            else -movement_stock_quantity
        )
        reserved_delta = -reserved_release_stock_quantity
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
        if unit_cost is None:
            stock_unit_cost = float(balance.average_cost or 0.0)
            effective_unit_cost = stock_unit_cost * resolve_item_uom_factor(item, normalized_uom, label="Movement UOM")
        else:
            effective_unit_cost = normalize_nonnegative_quantity(unit_cost, label="Unit cost")
            stock_unit_cost = convert_item_unit_cost_to_stock(
                item,
                effective_unit_cost,
                uom=normalized_uom,
                label="Unit cost",
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
                quantity=movement_stock_quantity,
                unit_cost=stock_unit_cost,
            )
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


__all__ = ["StockControlMovementMixin"]
