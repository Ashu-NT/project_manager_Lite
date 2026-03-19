from __future__ import annotations

from abc import ABC, abstractmethod

from core.modules.inventory_procurement.domain import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequisition,
    PurchaseRequisitionLine,
    ReceiptHeader,
    ReceiptLine,
    StockBalance,
    StockItem,
    StockTransaction,
    Storeroom,
)


class StockItemRepository(ABC):
    @abstractmethod
    def add(self, item: StockItem) -> None: ...

    @abstractmethod
    def update(self, item: StockItem) -> None: ...

    @abstractmethod
    def get(self, item_id: str) -> StockItem | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, item_code: str) -> StockItem | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[StockItem]: ...


class StoreroomRepository(ABC):
    @abstractmethod
    def add(self, storeroom: Storeroom) -> None: ...

    @abstractmethod
    def update(self, storeroom: Storeroom) -> None: ...

    @abstractmethod
    def get(self, storeroom_id: str) -> Storeroom | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, storeroom_code: str) -> Storeroom | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> list[Storeroom]: ...


class StockBalanceRepository(ABC):
    @abstractmethod
    def add(self, balance: StockBalance) -> None: ...

    @abstractmethod
    def update(self, balance: StockBalance) -> None: ...

    @abstractmethod
    def get(self, balance_id: str) -> StockBalance | None: ...

    @abstractmethod
    def get_for_stock_position(
        self,
        organization_id: str,
        stock_item_id: str,
        storeroom_id: str,
    ) -> StockBalance | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
    ) -> list[StockBalance]: ...


class StockTransactionRepository(ABC):
    @abstractmethod
    def add(self, transaction: StockTransaction) -> None: ...

    @abstractmethod
    def get(self, transaction_id: str) -> StockTransaction | None: ...

    @abstractmethod
    def get_by_number(self, organization_id: str, transaction_number: str) -> StockTransaction | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        limit: int = 200,
    ) -> list[StockTransaction]: ...


class PurchaseRequisitionRepository(ABC):
    @abstractmethod
    def add(self, requisition: PurchaseRequisition) -> None: ...

    @abstractmethod
    def update(self, requisition: PurchaseRequisition) -> None: ...

    @abstractmethod
    def get(self, requisition_id: str) -> PurchaseRequisition | None: ...

    @abstractmethod
    def get_by_number(self, organization_id: str, requisition_number: str) -> PurchaseRequisition | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        status: str | None = None,
        site_id: str | None = None,
        storeroom_id: str | None = None,
        limit: int = 200,
    ) -> list[PurchaseRequisition]: ...


class PurchaseRequisitionLineRepository(ABC):
    @abstractmethod
    def add(self, line: PurchaseRequisitionLine) -> None: ...

    @abstractmethod
    def update(self, line: PurchaseRequisitionLine) -> None: ...

    @abstractmethod
    def get(self, line_id: str) -> PurchaseRequisitionLine | None: ...

    @abstractmethod
    def list_for_requisition(self, requisition_id: str) -> list[PurchaseRequisitionLine]: ...


class PurchaseOrderRepository(ABC):
    @abstractmethod
    def add(self, purchase_order: PurchaseOrder) -> None: ...

    @abstractmethod
    def update(self, purchase_order: PurchaseOrder) -> None: ...

    @abstractmethod
    def get(self, purchase_order_id: str) -> PurchaseOrder | None: ...

    @abstractmethod
    def get_by_number(self, organization_id: str, po_number: str) -> PurchaseOrder | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        status: str | None = None,
        site_id: str | None = None,
        supplier_party_id: str | None = None,
        limit: int = 200,
    ) -> list[PurchaseOrder]: ...


class PurchaseOrderLineRepository(ABC):
    @abstractmethod
    def add(self, line: PurchaseOrderLine) -> None: ...

    @abstractmethod
    def update(self, line: PurchaseOrderLine) -> None: ...

    @abstractmethod
    def get(self, line_id: str) -> PurchaseOrderLine | None: ...

    @abstractmethod
    def list_for_purchase_order(self, purchase_order_id: str) -> list[PurchaseOrderLine]: ...

    @abstractmethod
    def list_for_requisition_line(self, requisition_line_id: str) -> list[PurchaseOrderLine]: ...


class ReceiptHeaderRepository(ABC):
    @abstractmethod
    def add(self, receipt: ReceiptHeader) -> None: ...

    @abstractmethod
    def get(self, receipt_id: str) -> ReceiptHeader | None: ...

    @abstractmethod
    def get_by_number(self, organization_id: str, receipt_number: str) -> ReceiptHeader | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        purchase_order_id: str | None = None,
        limit: int = 200,
    ) -> list[ReceiptHeader]: ...


class ReceiptLineRepository(ABC):
    @abstractmethod
    def add(self, line: ReceiptLine) -> None: ...

    @abstractmethod
    def get(self, line_id: str) -> ReceiptLine | None: ...

    @abstractmethod
    def list_for_receipt(self, receipt_id: str) -> list[ReceiptLine]: ...


__all__ = [
    "PurchaseOrderLineRepository",
    "PurchaseOrderRepository",
    "PurchaseRequisitionLineRepository",
    "PurchaseRequisitionRepository",
    "ReceiptHeaderRepository",
    "ReceiptLineRepository",
    "StockBalanceRepository",
    "StockItemRepository",
    "StockTransactionRepository",
    "StoreroomRepository",
]
