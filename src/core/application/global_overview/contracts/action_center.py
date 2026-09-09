from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ActionCenterContext:
    user_id: str
    tenant_id: str
    organization_id: str


@dataclass(frozen=True, slots=True)
class ActionCenterItemDto:
    id: str
    kind: str
    title: str
    module: str
    subject_type: str
    subject_id: str
    subject_display: str
    action_state: str
    route_id: str
    priority: str | None = None
    due_at: date | None = None


@dataclass(frozen=True, slots=True)
class ActionCenterSummaryDto:
    all_action_items: int
    reviews_and_approvals: int
    assigned_work: int
    submissions: int


@dataclass(frozen=True, slots=True)
class ActionCenterContribution:
    """One contributor's exact answer for its own actionable items.

    `items` is a bounded set of preview candidates the contributor considers
    worth surfacing first -- it is not required to be the contributor's full
    matching set, and the aggregator must never derive counts from it.
    `summary` is the contributor's exact count over its complete matching
    set, computed however the contributor can do so efficiently (e.g. a
    database COUNT), independent of how many items it chose to preview.
    """

    items: tuple[ActionCenterItemDto, ...]
    summary: ActionCenterSummaryDto


class ActionCenterContributor(Protocol):
    def collect(
        self,
        context: ActionCenterContext,
        preview_limit: int,
    ) -> ActionCenterContribution: ...


__all__ = [
    "ActionCenterContext",
    "ActionCenterItemDto",
    "ActionCenterSummaryDto",
    "ActionCenterContribution",
    "ActionCenterContributor",
]
