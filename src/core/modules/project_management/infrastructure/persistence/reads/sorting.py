from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.core.modules.project_management.contracts.reads.sorting import (
    ReadSort,
    ReadSortDirection,
)


def stable_order_by(
    *,
    sort: ReadSort,
    expressions: Mapping[str, Sequence[Any]],
    default_key: str,
    tie_breakers: Sequence[Any],
) -> tuple[Any, ...]:
    """Resolve semantic sort keys to known SQL expressions only."""
    resolved = expressions.get(sort.key) or expressions[default_key]
    order = tuple(
        expression.desc()
        if sort.direction is ReadSortDirection.DESCENDING
        else expression.asc()
        for expression in resolved
    )
    return (*order, *(expression.asc() for expression in tie_breakers))


__all__ = ["stable_order_by"]
