from __future__ import annotations

from abc import ABC, abstractmethod

from core.modules.inventory_procurement.domain import StockItem, Storeroom


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


__all__ = ["StockItemRepository", "StoreroomRepository"]
