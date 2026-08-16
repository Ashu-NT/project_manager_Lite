from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.core.platform.integration.delivery import (
    IntegrationInboxReceipt,
    IntegrationOutboxRecord,
)


class IntegrationOutboxRepository(ABC):
    @abstractmethod
    def add(self, record: IntegrationOutboxRecord) -> None: ...

    @abstractmethod
    def get(self, record_id: str) -> IntegrationOutboxRecord | None: ...

    @abstractmethod
    def get_by_event_id(self, event_id: str) -> IntegrationOutboxRecord | None: ...

    @abstractmethod
    def get_latest_by_aggregate(
        self, *, aggregate_type: str, aggregate_id: str
    ) -> IntegrationOutboxRecord | None: ...

    @abstractmethod
    def claim_available(
        self,
        *,
        now: datetime,
        lease_token: str,
        lease_expires_at: datetime,
        limit: int,
    ) -> list[IntegrationOutboxRecord]: ...

    @abstractmethod
    def update(self, record: IntegrationOutboxRecord, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...


class IntegrationInboxRepository(ABC):
    @abstractmethod
    def add(self, receipt: IntegrationInboxReceipt) -> None: ...

    @abstractmethod
    def get(self, receipt_id: str) -> IntegrationInboxReceipt | None: ...

    @abstractmethod
    def get_by_deduplication_key(
        self, deduplication_key: str, *, for_update: bool = False
    ) -> IntegrationInboxReceipt | None: ...

    @abstractmethod
    def latest_processed_aggregate_version(
        self, *, consumer_name: str, aggregate_type: str, aggregate_id: str
    ) -> int | None: ...

    @abstractmethod
    def claim_available(
        self,
        *,
        now: datetime,
        lease_token: str,
        lease_expires_at: datetime,
        limit: int,
    ) -> list[IntegrationInboxReceipt]: ...

    @abstractmethod
    def update(self, receipt: IntegrationInboxReceipt, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...


__all__ = ["IntegrationInboxRepository", "IntegrationOutboxRepository"]
