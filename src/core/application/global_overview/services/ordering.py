from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from src.core.application.global_overview.contracts.action_center import ActionCenterItemDto

# Tier 3 (no due_at) filler for the due_at sort column, so every item's key
# has the same shape/type per column regardless of tier -- never actually
# compared across tiers, since tier is the primary sort key.
_NO_DUE_AT_FILLER = date.max
_NO_RECENCY = float("inf")


def _recency_rank(source_timestamp: datetime | None) -> float:
    """Larger = older/missing, so ascending sort naturally puts the newest
    real timestamp first and items with no timestamp at all last.

    Deliberately avoids datetime.timestamp() -- datetime.min.timestamp()
    raises OSError on Windows, and this needs to be safe for any legitimate
    source timestamp, not just recent ones.
    """
    if source_timestamp is None:
        return _NO_RECENCY
    ordinal_seconds = source_timestamp.toordinal() * 86400 + (
        source_timestamp.hour * 3600 + source_timestamp.minute * 60 + source_timestamp.second
    )
    return -float(ordinal_seconds)


def _sort_key(item: ActionCenterItemDto, *, today: date) -> tuple:
    if item.due_at is not None:
        if item.due_at < today:
            tier = 0  # genuinely overdue -- earliest (most overdue) due_at first
        elif item.due_at == today:
            tier = 1  # due today
        else:
            tier = 2  # due in the future -- earliest first
        due_rank = item.due_at
        recency_rank = 0.0
    else:
        tier = 3  # no due date -- most recent relevant timestamp first
        due_rank = _NO_DUE_AT_FILLER
        recency_rank = _recency_rank(item.source_timestamp)
    return (tier, due_rank, recency_rank, item.module, item.kind, item.id)


def sort_action_center_items(
    items: Iterable[ActionCenterItemDto],
    *,
    today: date,
) -> tuple[ActionCenterItemDto, ...]:
    """The one deterministic Action Center ordering, shared by every
    contributor (to pick its own bounded preview) and by ActionCenterService
    (to order the merged global preview) -- never database default order,
    contributor registration order, or plain concatenation order.

    Order:
    1. genuinely overdue items with a real due_at, most overdue first
    2. items due today
    3. remaining items with a real due_at, earliest first
    4. no-due-date items, most recent relevant timestamp first
    5. stable tie-breaker: module, kind, id
    """
    return tuple(sorted(items, key=lambda item: _sort_key(item, today=today)))


__all__ = ["sort_action_center_items"]
