from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop.inventory.models import (
    InventoryStockBalanceDesktopDto,
    InventoryStockTransactionDesktopDto,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.serializers import (
    serialize_balance,
    serialize_transaction,
)


class InventoryDesktopBalanceMixin:
    def list_balances(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
    ) -> tuple[InventoryStockBalanceDesktopDto, ...]:
        if self._stock_service is None:
            return ()
        item_lookup = {row.value: row.label for row in self.list_items(active_only=None)}
        storeroom_lookup = {
            row.value: row.label
            for row in self.list_storeroom_options(active_only=None)
        }
        rows = sorted(
            self._stock_service.list_balances(
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
            ),
            key=lambda row: (
                not bool(getattr(row, "reorder_required", False)),
                str(getattr(row, "storeroom_id", "") or "").casefold(),
                str(getattr(row, "stock_item_id", "") or "").casefold(),
            ),
        )
        return tuple(
            serialize_balance(
                row,
                item_lookup=item_lookup,
                storeroom_lookup=storeroom_lookup,
            )
            for row in rows
        )

    def list_transactions(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        limit: int = 200,
    ) -> tuple[InventoryStockTransactionDesktopDto, ...]:
        if self._stock_service is None:
            return ()
        item_lookup = {row.value: row.label for row in self.list_items(active_only=None)}
        storeroom_lookup = {
            row.value: row.label
            for row in self.list_storeroom_options(active_only=None)
        }
        rows = self._stock_service.list_transactions(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            limit=limit,
        )
        return tuple(
            serialize_transaction(
                row,
                item_lookup=item_lookup,
                storeroom_lookup=storeroom_lookup,
            )
            for row in rows
        )

    def _serialize_transaction(self, row) -> InventoryStockTransactionDesktopDto:
        item_lookup = {entry.value: entry.label for entry in self.list_items(active_only=None)}
        storeroom_lookup = {
            entry.value: entry.label
            for entry in self.list_storeroom_options(active_only=None)
        }
        return serialize_transaction(
            row,
            item_lookup=item_lookup,
            storeroom_lookup=storeroom_lookup,
        )


__all__ = ["InventoryDesktopBalanceMixin"]
