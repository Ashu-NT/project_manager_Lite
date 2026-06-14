from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.activity.domain.activity_entry import ActivityEntry


class ActivityRepository(ABC):
    @abstractmethod
    def add(self, entry: ActivityEntry) -> None: ...

    @abstractmethod
    def list_recent(
        self,
        limit: int = 200,
        *,
        tenant_id: str | None = None,
        organization_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        module: str | None = None,
        workspace_id: str | None = None,
    ) -> list[ActivityEntry]: ...


__all__ = ["ActivityRepository"]
