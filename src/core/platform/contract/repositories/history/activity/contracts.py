from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from src.core.platform.domain.history.activity.activity_entry import ActivityEntry


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
        entity_types: Sequence[str] | None = None,
        entity_id: str | None = None,
        module: str | None = None,
        workspace_id: str | None = None,
        parent_entity_id: str | None = None,
        action_prefix: str | None = None,
    ) -> list[ActivityEntry]:
        """`organization_id` may be any organization within the caller's
        tenant, not just their active one -- Organization Detail reads
        activity for whichever organization it is showing."""
        ...

    @abstractmethod
    def list_page_recent(
        self,
        *,
        page: int,
        page_size: int,
        tenant_id: str | None = None,
        organization_id: str | None = None,
        entity_type: str | None = None,
        entity_types: Sequence[str] | None = None,
        module: str | None = None,
        search: str | None = None,
        since=None,
    ) -> tuple[list[ActivityEntry], int, int]:
        """Paginated variant of `list_recent` for a full activity workspace
        (e.g. Organization Detail's Activity tab) rather than a bounded
        preview -- same organization-scoping rule as `list_recent`, plus
        server-side search (against the stored human_message) and an
        optional `since` cutoff datetime. Returns
        (page_items, total_count, filtered_total_count)."""
        ...


__all__ = ["ActivityRepository"]
