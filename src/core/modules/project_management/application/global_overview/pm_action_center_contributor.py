from __future__ import annotations

from src.core.global_overview.contract.action_center import (
    ActionCenterContext,
    ActionCenterContribution,
    ActionCenterContributor,
    ActionCenterCursor,
)


class ProjectManagementActionCenterContributor:
    """Module-owned bounded read adapter; business mutations stay in their services."""

    def __init__(self, *, reader: ActionCenterContributor) -> None:
        self._reader = reader

    def collect(
        self,
        context: ActionCenterContext,
        preview_limit: int,
        *,
        after: ActionCenterCursor | None = None,
    ) -> ActionCenterContribution:
        return self._reader.collect(context, preview_limit, after=after)


__all__ = ["ProjectManagementActionCenterContributor"]
