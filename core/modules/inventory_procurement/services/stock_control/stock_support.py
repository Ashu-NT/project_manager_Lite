from __future__ import annotations

from uuid import uuid4

from core.modules.inventory_procurement.domain import StockBalance, StockItem, StockTransaction, StockTransactionType, Storeroom
from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.common.models import Organization


def build_transaction_number() -> str:
    return f"INV-TXN-{uuid4().hex[:10].upper()}"


class StockControlSupportMixin:
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


__all__ = ["StockControlSupportMixin", "build_transaction_number"]
