"""Canonical Task->Task dependency scheduling mathematics.

Single authority for how a TaskDependency's (dependency_type, lag_days) turns
into a scheduling constraint, in both the forward (earliest dates) and
backward (latest dates) CPM passes. Before this module existed, the same
FS/SS/FF/SF formulas were hand-duplicated across SchedulingEngine,
CPMCalculator, TaskDependencyDiagnosticsMixin, and DependencyResolver, and
had drifted: SS/FF/SF's lag was off by one working day relative to FS, and
the backward pass was not a true inverse for anything but FS (see
docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
sections 5 and 11 for the full defect writeup this module fixes).

Design principle: forward and backward formulas are derived from the SAME
per-type definition below, via ``shift_working_days`` with a sign flip. They
cannot drift from each other because there is only one formula, applied in
two directions -- there is no second, independently-written backward
formula to keep in sync.

Canonical zero-lag semantics (product decision, not derived from the old
code):

    FINISH_TO_START (FS), lag 0: successor starts the first working day
        AFTER the predecessor finishes (boundary offset = +1 from the
        predecessor's finish).
    START_TO_START (SS), lag 0: successor may start ON the predecessor's
        start working day (boundary offset = 0 from the predecessor's
        start).
    FINISH_TO_FINISH (FF), lag 0: successor may finish ON the predecessor's
        finish working day (boundary offset = 0 from the predecessor's
        finish).
    START_TO_FINISH (SF), lag 0: successor may finish ON the predecessor's
        start working day (boundary offset = 0 from the predecessor's
        start).

Positive lag_days adds that many additional working days of separation
beyond the zero-lag boundary. Negative lag_days ("lead") moves the boundary
earlier by that many working days -- and is strictly monotonic, because
every unit of lag is one full step of ``shift_working_days``, never a
constant that happens to interact with an inclusive/exclusive counting
quirk (unlike the old ``lag+2``/bare-``lag`` formulas it replaces).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.modules.project_management.domain.enums import DependencyType

# Zero-lag boundary offset (in working days, per shift_working_days) from the
# relationship's anchor date to the constrained successor/predecessor date.
_ZERO_LAG_BOUNDARY_OFFSET: dict[DependencyType, int] = {
    DependencyType.FINISH_TO_START: 1,
    DependencyType.START_TO_START: 0,
    DependencyType.FINISH_TO_FINISH: 0,
    DependencyType.START_TO_FINISH: 0,
}

# Which of the predecessor's two computed dates anchors the relationship.
_ANCHOR_IS_FINISH: dict[DependencyType, bool] = {
    DependencyType.FINISH_TO_START: True,
    DependencyType.START_TO_START: False,
    DependencyType.FINISH_TO_FINISH: True,
    DependencyType.START_TO_FINISH: False,
}

# Which of the successor's two dates the relationship constrains.
_CONSTRAINS_SUCCESSOR_START: dict[DependencyType, bool] = {
    DependencyType.FINISH_TO_START: True,
    DependencyType.START_TO_START: True,
    DependencyType.FINISH_TO_FINISH: False,
    DependencyType.START_TO_FINISH: False,
}


class UnsupportedDependencyTypeError(ValueError):
    """Raised when a dependency carries a dependency_type this module does
    not recognize. Every dispatch site in this module fails closed"""


def normalize_forward(calendar: CalendarProtocol, anchor: date) -> date:
    """Round ``anchor`` forward to itself (if already a working day) or the
    next working day. Used before applying any lag/lead shift, so a
    non-working anchor (e.g. a root task's raw ``start_date`` with no
    calendar snapping) never silently survives into the relationship math"""
    return calendar.next_working_day(anchor, include_today=True)


def shift_working_days(calendar: CalendarProtocol, anchor: date, signed_offset: int) -> date:
    """Explicit, monotonic working-day shift primitive.

    0 = anchor itself (assumed already a working day -- normalize first).
    +1 = the next working day strictly after anchor.
    -1 = the previous working day strictly before anchor.

    Every non-zero offset is a full, distinct step -- there is no
    inclusive/exclusive counting asymmetry to compensate for with magic
    constants, unlike the calendar's own ``add_working_days`` (whose n=0
    short-circuit and inclusive-positive/exclusive-negative counting is
    exactly what caused the old lag arithmetic to be inconsistent per type
    and non-monotonic for negative lag).
    """
    if signed_offset == 0:
        return anchor
    if signed_offset > 0:
        current = anchor
        remaining = signed_offset
        while remaining > 0:
            current += timedelta(days=1)
            if calendar.is_working_day(current):
                remaining -= 1
        return current
    current = anchor
    remaining = -signed_offset
    while remaining > 0:
        current -= timedelta(days=1)
        if calendar.is_working_day(current):
            remaining -= 1
    return current


def _boundary_offset(dependency_type: DependencyType) -> int:
    try:
        return _ZERO_LAG_BOUNDARY_OFFSET[dependency_type]
    except KeyError as exc:
        raise UnsupportedDependencyTypeError(
            f"Unsupported dependency type: {dependency_type!r}."
        ) from exc


def relationship_anchor_is_predecessor_finish(dependency_type: DependencyType) -> bool:
    """True when the relationship anchors off the predecessor's finish
    (FS/FF); False when it anchors off the predecessor's start (SS/SF)."""
    if dependency_type not in _ANCHOR_IS_FINISH:
        raise UnsupportedDependencyTypeError(
            f"Unsupported dependency type: {dependency_type!r}."
        )
    return _ANCHOR_IS_FINISH[dependency_type]


def relationship_constrains_successor_start(dependency_type: DependencyType) -> bool:
    """True when the relationship constrains the successor's START (FS/SS);
    False when it constrains the successor's FINISH (FF/SF)."""
    if dependency_type not in _CONSTRAINS_SUCCESSOR_START:
        raise UnsupportedDependencyTypeError(
            f"Unsupported dependency type: {dependency_type!r}."
        )
    return _CONSTRAINS_SUCCESSOR_START[dependency_type]


@dataclass(frozen=True, slots=True)
class SuccessorBoundary:
    """The single date a dependency edge contributes to the successor's
    forward-pass computation, plus which of the successor's own dates
    (start or finish) it constrains."""

    date: date
    constrains_start: bool


def successor_boundary(
    calendar: CalendarProtocol,
    *,
    dependency_type: DependencyType,
    lag_days: int,
    predecessor_earliest_start: date | None,
    predecessor_earliest_finish: date | None,
) -> SuccessorBoundary | None:
    """Forward-pass contribution of one dependency edge.

    Returns None if the anchor date this relationship needs (predecessor ES
    for SS/SF, predecessor EF for FS/FF) is not yet known -- mirrors the old
    per-engine ``if pred_ef:``/``if pred_es:`` guards, but as one shared
    check instead of four duplicated ones.
    """
    offset = _boundary_offset(dependency_type)
    anchor_is_finish = relationship_anchor_is_predecessor_finish(dependency_type)
    anchor = predecessor_earliest_finish if anchor_is_finish else predecessor_earliest_start
    if anchor is None:
        return None
    normalized_anchor = normalize_forward(calendar, anchor)
    boundary_date = shift_working_days(calendar, normalized_anchor, offset + lag_days)
    return SuccessorBoundary(
        date=boundary_date,
        constrains_start=relationship_constrains_successor_start(dependency_type),
    )


def successor_earliest_start_from_boundary(
    calendar: CalendarProtocol,
    boundary: SuccessorBoundary,
    *,
    successor_duration_days: int,
) -> date:
    """Convert a SuccessorBoundary into the successor's earliest START.

    If the boundary constrains the successor's start directly (FS/SS), the
    boundary date IS the earliest start. If it constrains the successor's
    finish (FF/SF), the earliest start is back-solved by walking backward
    the task's own duration, using the same shift primitive (never the
    calendar's ``add_working_days``, so the back-solve can't reintroduce the
    inclusive/exclusive inconsistency this module exists to remove).
    """
    if boundary.constrains_start:
        return boundary.date
    if successor_duration_days > 0:
        return shift_working_days(calendar, boundary.date, -(successor_duration_days - 1))
    return boundary.date


@dataclass(frozen=True, slots=True)
class PredecessorLateBoundary:
    """The single late-date bound one outgoing dependency edge contributes
    to the predecessor's backward-pass computation, expressed as a LATEST
    START bound (see module docstring: forward and backward share one
    formula, applied with a sign flip, so both FS/SS-style "start-anchored"
    and FF/SF-style "finish-anchored" edges are normalized into the same LS
    unit before any predecessor-level minimum is taken -- this is what fixes
    the old mixed-successor-type shadowing bug)."""

    latest_start: date


def predecessor_late_boundary(
    calendar: CalendarProtocol,
    *,
    dependency_type: DependencyType,
    lag_days: int,
    successor_latest_start: date | None,
    successor_latest_finish: date | None,
    predecessor_duration_days: int,
) -> PredecessorLateBoundary | None:
    """Backward-pass contribution of one outgoing dependency edge, expressed
    as a bound on the PREDECESSOR's latest start.

    This is the exact algebraic inverse of ``successor_boundary``: the same
    offset (zero-lag boundary + lag_days) is applied with
    ``shift_working_days`` in the negative direction from whichever of the
    successor's late dates the relationship reads (LS for FS/SS-derived
    edges -- i.e. edges whose forward form constrains the successor's
    start; LF for FF/SF-derived edges).
    """
    offset = _boundary_offset(dependency_type)
    constrains_successor_start = relationship_constrains_successor_start(dependency_type)
    successor_date = successor_latest_start if constrains_successor_start else successor_latest_finish
    if successor_date is None:
        return None
    anchor_is_finish = relationship_anchor_is_predecessor_finish(dependency_type)
    predecessor_late_anchor_date = shift_working_days(calendar, successor_date, -(offset + lag_days))
    if anchor_is_finish:
        # predecessor_late_anchor_date is a bound on the predecessor's LATEST
        # FINISH (FS/FF) -- convert to LATEST START via the same duration
        # back-solve used on the forward side.
        if predecessor_duration_days > 0:
            latest_start = shift_working_days(
                calendar, predecessor_late_anchor_date, -(predecessor_duration_days - 1)
            )
        else:
            latest_start = predecessor_late_anchor_date
    else:
        # predecessor_late_anchor_date is already a bound on the
        # predecessor's LATEST START (SS/SF).
        latest_start = predecessor_late_anchor_date
    return PredecessorLateBoundary(latest_start=latest_start)


__all__ = [
    "UnsupportedDependencyTypeError",
    "SuccessorBoundary",
    "PredecessorLateBoundary",
    "normalize_forward",
    "shift_working_days",
    "relationship_anchor_is_predecessor_finish",
    "relationship_constrains_successor_start",
    "successor_boundary",
    "successor_earliest_start_from_boundary",
    "predecessor_late_boundary",
]
