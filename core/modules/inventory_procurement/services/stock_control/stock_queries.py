from __future__ import annotations

from core.modules.inventory_procurement.domain import StockBalance, StockTransaction
from core.modules.inventory_procurement.support import normalize_optional_text
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.platform.common.exceptions import NotFoundError


class StockControlQueryMixin:
    def list_balances(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
    ) -> list[StockBalance]:
        self._require_read("list stock balances")
        organization = self._active_organization()
        rows = self._balance_repo.list_for_organization(
            organization.id,
            stock_item_id=normalize_optional_text(stock_item_id) or None,
            storeroom_id=normalize_optional_text(storeroom_id) or None,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="storeroom",
            permission_code="inventory.read",
            scope_id_getter=lambda row: getattr(row, "storeroom_id", ""),
        )

    def get_balance(self, balance_id: str) -> StockBalance:
        self._require_read("view stock balance")
        organization = self._active_organization()
        balance = self._balance_repo.get(balance_id)
        if balance is None or balance.organization_id != organization.id:
            raise NotFoundError("Stock balance not found in the active organization.", code="INVENTORY_STOCK_BALANCE_NOT_FOUND")
        require_scope_permission(
            self._user_session,
            "storeroom",
            balance.storeroom_id,
            "inventory.read",
            operation_label="view stock balance",
        )
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
        rows = self._transaction_repo.list_for_organization(
            organization.id,
            stock_item_id=normalize_optional_text(stock_item_id) or None,
            storeroom_id=normalize_optional_text(storeroom_id) or None,
            limit=max(1, int(limit or 200)),
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="storeroom",
            permission_code="inventory.read",
            scope_id_getter=lambda row: getattr(row, "storeroom_id", ""),
        )


__all__ = ["StockControlQueryMixin"]
