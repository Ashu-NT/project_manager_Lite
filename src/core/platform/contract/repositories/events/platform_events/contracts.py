from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.common.exceptions import OperationNotPermittedError
from src.core.platform.domain.events.platform_events.platform_event import PlatformEvent


class PlatformEventRepository(ABC):

    @abstractmethod
    def add(self, event: PlatformEvent) -> None: ...

    @abstractmethod
    def list_for_tenant(self, tenant_id: str, *, limit: int = 100) -> list[PlatformEvent]: ...

    @abstractmethod
    def list_for_resource(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        *,
        limit: int = 100,
    ) -> list[PlatformEvent]: ...

    def update(self, event: PlatformEvent) -> None:
        raise OperationNotPermittedError(
            "PlatformEvent records are append-only and cannot be updated.",
            code="PLATFORM_EVENT_IMMUTABLE",
        )

    def delete(self, event_id: str) -> None:
        raise OperationNotPermittedError(
            "PlatformEvent records are append-only and cannot be deleted.",
            code="PLATFORM_EVENT_IMMUTABLE",
        )


__all__ = ["PlatformEventRepository"]
