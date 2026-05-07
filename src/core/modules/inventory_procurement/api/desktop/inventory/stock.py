from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop.inventory.models import (
    InventoryAdjustmentCommand,
    InventoryIssueCommand,
    InventoryOpeningBalanceCommand,
    InventoryReturnCommand,
    InventoryStockBalanceDesktopDto,
    InventoryStockTransactionDesktopDto,
    InventoryTransferCommand,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.serializers import (
    serialize_balance,
    serialize_transaction,
)


class InventoryDesktopStockMixin:
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

    def post_opening_balance(
        self,
        command: InventoryOpeningBalanceCommand,
    ) -> InventoryStockTransactionDesktopDto:
        transaction = self._require_stock_service().post_opening_balance(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            quantity=command.quantity,
            uom=command.uom,
            unit_cost=command.unit_cost,
            transaction_at=command.transaction_at,
            notes=command.notes,
        )
        return self._serialize_transaction(transaction)

    def post_adjustment(
        self,
        command: InventoryAdjustmentCommand,
    ) -> InventoryStockTransactionDesktopDto:
        transaction = self._require_stock_service().post_adjustment(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            quantity=command.quantity,
            direction=command.direction,
            uom=command.uom,
            unit_cost=command.unit_cost,
            transaction_at=command.transaction_at,
            reference_type=command.reference_type,
            reference_id=command.reference_id,
            notes=command.notes,
        )
        return self._serialize_transaction(transaction)

    def issue_stock(
        self,
        command: InventoryIssueCommand,
    ) -> InventoryStockTransactionDesktopDto:
        transaction = self._require_stock_service().issue_stock(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            quantity=command.quantity,
            uom=command.uom,
            unit_cost=command.unit_cost,
            transaction_at=command.transaction_at,
            release_reserved_qty=command.release_reserved_qty,
            reference_type=command.reference_type,
            reference_id=command.reference_id,
            notes=command.notes,
        )
        return self._serialize_transaction(transaction)

    def return_stock(
        self,
        command: InventoryReturnCommand,
    ) -> InventoryStockTransactionDesktopDto:
        transaction = self._require_stock_service().return_stock(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            quantity=command.quantity,
            uom=command.uom,
            unit_cost=command.unit_cost,
            transaction_at=command.transaction_at,
            reference_type=command.reference_type,
            reference_id=command.reference_id,
            notes=command.notes,
        )
        return self._serialize_transaction(transaction)

    def transfer_stock(
        self,
        command: InventoryTransferCommand,
    ) -> tuple[InventoryStockTransactionDesktopDto, InventoryStockTransactionDesktopDto]:
        outbound, inbound = self._require_stock_service().transfer_stock(
            stock_item_id=command.stock_item_id,
            source_storeroom_id=command.source_storeroom_id,
            destination_storeroom_id=command.destination_storeroom_id,
            quantity=command.quantity,
            uom=command.uom,
            transaction_at=command.transaction_at,
            notes=command.notes,
        )
        return (
            self._serialize_transaction(outbound),
            self._serialize_transaction(inbound),
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


__all__ = ["InventoryDesktopStockMixin"]
