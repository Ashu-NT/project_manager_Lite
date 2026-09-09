from __future__ import annotations

from datetime import date
from typing import Iterable

from src.core.application.global_overview.contracts.action_center import (
    ActionCenterContext,
    ActionCenterContribution,
    ActionCenterContributor,
    ActionCenterSummaryDto,
)
from src.core.application.global_overview.services.ordering import sort_action_center_items


def _sum_summaries(summaries: Iterable[ActionCenterSummaryDto]) -> ActionCenterSummaryDto:
    all_action_items = 0
    reviews_and_approvals = 0
    assigned_work = 0
    submissions = 0
    for summary in summaries:
        all_action_items += summary.all_action_items
        reviews_and_approvals += summary.reviews_and_approvals
        assigned_work += summary.assigned_work
        submissions += summary.submissions
    return ActionCenterSummaryDto(
        all_action_items=all_action_items,
        reviews_and_approvals=reviews_and_approvals,
        assigned_work=assigned_work,
        submissions=submissions,
    )


class ActionCenterService:
    """Aggregates independently-owned contributor summaries and bounded
    preview candidates into one normalized Action Center answer.

    Never loads every actionable row to compute the Overview counts: each
    contributor is responsible for its own exact, efficient count. This
    service only sums already-exact summaries and merges already-bounded
    preview candidates -- it never re-derives a count from a (possibly
    truncated) items list, so the two can never drift apart. Contributor
    registration order never affects the result -- the merged candidates
    are always re-ordered by `sort_action_center_items` before truncation.
    """

    def __init__(self, *, contributors: tuple[ActionCenterContributor, ...]) -> None:
        self._contributors = contributors

    def build(
        self,
        context: ActionCenterContext,
        *,
        preview_limit: int = 50,
        today: date | None = None,
    ) -> ActionCenterContribution:
        contributions = tuple(
            contributor.collect(context, preview_limit) for contributor in self._contributors
        )
        summary = _sum_summaries(contribution.summary for contribution in contributions)
        merged_items = [item for contribution in contributions for item in contribution.items]
        ordered = sort_action_center_items(merged_items, today=today or date.today())
        return ActionCenterContribution(items=ordered[:preview_limit], summary=summary)


__all__ = ["ActionCenterService"]
