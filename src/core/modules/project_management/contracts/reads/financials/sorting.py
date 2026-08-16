from __future__ import annotations

from src.core.modules.project_management.contracts.reads.sorting import (
    ReadSort,
    ReadSortDirection,
)


COST_ENTRY_SORT_KEYS = frozenset({"title", "statusLabel", "metaText"})
COMMITMENT_SORT_KEYS = frozenset({"title", "statusLabel", "metaText"})


def normalize_cost_entry_sort(*, key: object, direction: object) -> ReadSort:
    return ReadSort.normalize(
        key=key,
        direction=direction,
        allowed_keys=COST_ENTRY_SORT_KEYS,
        default_key="metaText",
        default_direction=ReadSortDirection.DESCENDING,
    )


def normalize_commitment_sort(*, key: object, direction: object) -> ReadSort:
    return ReadSort.normalize(
        key=key,
        direction=direction,
        allowed_keys=COMMITMENT_SORT_KEYS,
        default_key="metaText",
        default_direction=ReadSortDirection.DESCENDING,
    )


__all__ = [
    "COMMITMENT_SORT_KEYS",
    "COST_ENTRY_SORT_KEYS",
    "normalize_commitment_sort",
    "normalize_cost_entry_sort",
]
