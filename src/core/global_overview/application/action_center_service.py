from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from src.core.global_overview.application.ordering import (
    sort_action_center_items,
)
from src.core.global_overview.contract.action_center import (
    ActionCenterContext,
    ActionCenterContribution,
    ActionCenterContributor,
    ActionCenterCursor,
    ActionCenterSummaryDto,
)


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
        after: ActionCenterCursor | None = None,
    ) -> ActionCenterContribution:
        limit = min(100, max(0, int(preview_limit)))
        if after is not None and after.context != context:
            raise ValueError("Action Center cursor belongs to a different user or scope.")
        window = limit + 1 if limit else 0
        contributions = tuple(contributor.collect(context, window, after=after)
                              for contributor in self._contributors)
        if any(len(part.items) > window for part in contributions):
            raise ValueError("Action Center contributor exceeded its bounded query contract.")
        summary = _sum_summaries(contribution.summary for contribution in contributions)
        merged_items = [item for contribution in contributions for item in contribution.items]
        identities = {(item.module, item.kind, item.id) for item in merged_items}
        if len(identities) != len(merged_items):
            raise ValueError("Duplicate Action Center ownership: action contributed more than once.")
        ordered = sort_action_center_items(merged_items, today=today or date.today())
        items = ordered[:limit]
        cursor = None
        if items and len(ordered) > limit:
            last = items[-1]
            cursor = ActionCenterCursor(context, last.due_at, last.sort_at, last.module, last.kind, last.id)
        return ActionCenterContribution(items=items, summary=summary, next_cursor=cursor)


__all__ = ["ActionCenterService"]
