from __future__ import annotations

from collections.abc import Callable

from src.core.global_overview.contract.action_center import (
    ActionCenterContext,
    ActionCenterContribution,
    ActionCenterContributor,
    ActionCenterCursor,
    ActionCenterSummaryDto,
)


class ProjectManagementActionCenterContributor:
    """Module-owned bounded read adapter; business mutations stay in their services."""

    def __init__(self, *, reader: ActionCenterContributor, is_accessible: Callable[[], bool]) -> None:
        self._reader = reader
        self._is_accessible = is_accessible

    def collect(
        self,
        context: ActionCenterContext,
        preview_limit: int,
        *,
        after: ActionCenterCursor | None = None,
    ) -> ActionCenterContribution:
        if not self._is_accessible():
            return ActionCenterContribution((), ActionCenterSummaryDto(0, 0, 0, 0))
        return self._reader.collect(context, preview_limit, after=after)


__all__ = ["ProjectManagementActionCenterContributor"]
