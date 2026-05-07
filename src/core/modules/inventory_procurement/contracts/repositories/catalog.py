from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.inventory_procurement.domain.catalog.item import (
    InventoryItemCategory,
    StockItem,
)


class InventoryItemCategoryRepository(ABC):
    @abstractmethod
    def add(self, category: InventoryItemCategory) -> None: ...

    @abstractmethod
    def update(self, category: InventoryItemCategory) -> None: ...

    @abstractmethod
    def get(self, category_id: str) -> InventoryItemCategory | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, category_code: str) -> InventoryItemCategory | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        category_type: str | None = None,
    ) -> list[InventoryItemCategory]: ...


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
