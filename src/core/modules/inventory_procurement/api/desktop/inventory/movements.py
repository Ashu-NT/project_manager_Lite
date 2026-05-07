from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop.inventory.models import (
    InventoryAdjustmentCommand,
    InventoryIssueCommand,
    InventoryOpeningBalanceCommand,
    InventoryReturnCommand,
    InventoryStockTransactionDesktopDto,
    InventoryTransferCommand,
)


class InventoryDesktopMovementMixin:
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


__all__ = ["InventoryDesktopMovementMixin"]
