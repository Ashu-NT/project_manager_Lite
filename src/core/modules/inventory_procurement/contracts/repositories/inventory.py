from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.inventory_procurement.domain.inventory.stock import (
    StockBalance,
    StockReservation,
    StockTransaction,
    Storeroom,
)


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


class StockReservationRepository(ABC):
    @abstractmethod
    def add(self, reservation: StockReservation) -> None: ...

    @abstractmethod
    def update(self, reservation: StockReservation) -> None: ...

    @abstractmethod
    def get(self, reservation_id: str) -> StockReservation | None: ...

    @abstractmethod
    def get_by_number(self, organization_id: str, reservation_number: str) -> StockReservation | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[StockReservation]: ...
