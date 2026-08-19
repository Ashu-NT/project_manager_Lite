"""Single canonical source for Task scheduling-constraint presentation,
shared across the Tasks (editor), Scheduling (diagnostics), and Schedule
Impact desktop-API surfaces. Mirrors dependency_presentation.py's
"one map, not three independently-drifting copies" precedent -- see
docs/pm_modernization/R4_4_TASK_CONSTRAINT_CURRENT_STATE_AND_TARGET_GAPS.md,
which found exactly that already happening (a title-cased label in one
serializer, a raw unlabeled enum value in another, and a third,
hand-written panel that didn't even read the real enum).

ASAP is not a real ConstraintType member (see the audit, §6/§7) -- it is
the UI's name for "no constraint selected." It gets its own
ConstraintPresentation entry here (``value=None``) so the picker can
present it uniformly alongside the six real, editable types without any
consumer inventing a separate special case. DEADLINE is deliberately
NOT included in ``EDITABLE_CONSTRAINT_OPTIONS``: Task.constraint_type
rejects it outright (see domain/tasks/task.py), since task.deadline is
the real, separate field for that concept.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.enums import ConstraintType

# UI category -- deliberately NOT the validator's hard/soft split, which
# measures violation severity, not scheduling-boundary behavior (the
# audit's §5 finding). "Flexible" / "date boundary" / "fixed date" match
# how each type actually affects a schedule, per Phase L1.
CATEGORY_FLEXIBLE = "flexible"
CATEGORY_DATE_BOUNDARY = "date_boundary"
CATEGORY_FIXED_DATE = "fixed_date"


@dataclass(frozen=True)
class ConstraintPresentation:
    value: ConstraintType | None  # None means ASAP (no constraint)
    code: str  # e.g. "ASAP", "SNET", "MSO"
    label: str  # e.g. "Start No Earlier Than (SNET)"
    short_label: str  # e.g. "Start No Earlier Than" (no abbreviation suffix)
    description: str
    requires_date: bool
    category: str


_ASAP = ConstraintPresentation(
    value=None,
    code="ASAP",
    label="As Soon As Possible (ASAP)",
    short_label="As Soon As Possible",
    description="Task is scheduled from dependencies, duration and project calendar.",
    requires_date=False,
    category=CATEGORY_FLEXIBLE,
)

_EDITABLE: tuple[ConstraintPresentation, ...] = (
    _ASAP,
    ConstraintPresentation(
        value=ConstraintType.START_NO_EARLIER_THAN,
        code="SNET",
        label="Start No Earlier Than (SNET)",
        short_label="Start No Earlier Than",
        description="Task cannot start before the specified date.",
        requires_date=True,
        category=CATEGORY_DATE_BOUNDARY,
    ),
    ConstraintPresentation(
        value=ConstraintType.START_NO_LATER_THAN,
        code="SNLT",
        label="Start No Later Than (SNLT)",
        short_label="Start No Later Than",
        description="Task should start on or before the specified date.",
        requires_date=True,
        category=CATEGORY_DATE_BOUNDARY,
    ),
    ConstraintPresentation(
        value=ConstraintType.FINISH_NO_EARLIER_THAN,
        code="FNET",
        label="Finish No Earlier Than (FNET)",
        short_label="Finish No Earlier Than",
        description="Task cannot finish before the specified date.",
        requires_date=True,
        category=CATEGORY_DATE_BOUNDARY,
    ),
    ConstraintPresentation(
        value=ConstraintType.FINISH_NO_LATER_THAN,
        code="FNLT",
        label="Finish No Later Than (FNLT)",
        short_label="Finish No Later Than",
        description="Task should finish on or before the specified date.",
        requires_date=True,
        category=CATEGORY_DATE_BOUNDARY,
    ),
    ConstraintPresentation(
        value=ConstraintType.MUST_START_ON,
        code="MSO",
        label="Must Start On (MSO)",
        short_label="Must Start On",
        description="Fixes the task to the specified start date.",
        requires_date=True,
        category=CATEGORY_FIXED_DATE,
    ),
    ConstraintPresentation(
        value=ConstraintType.MUST_FINISH_ON,
        code="MFO",
        label="Must Finish On (MFO)",
        short_label="Must Finish On",
        description="Fixes the task to the specified finish date.",
        requires_date=True,
        category=CATEGORY_FIXED_DATE,
    ),
)

# DEADLINE is the one non-editable ConstraintType member (see the audit
# §3/§21) -- ConstraintValidator uses it purely to classify a
# task.deadline violation; it is never a Task.constraint_type value.
# Kept here only so a consumer rendering an arbitrary ConstraintViolation
# (which CAN legitimately carry ConstraintType.DEADLINE) has a label to
# show, without it ever appearing in the editable picker.
_DEADLINE = ConstraintPresentation(
    value=ConstraintType.DEADLINE,
    code="DEADLINE",
    label="Deadline",
    short_label="Deadline",
    description="Reports when the task's computed finish exceeds its deadline.",
    requires_date=True,
    category=CATEGORY_DATE_BOUNDARY,
)

EDITABLE_CONSTRAINT_OPTIONS: tuple[ConstraintPresentation, ...] = _EDITABLE

_BY_VALUE: dict[ConstraintType | None, ConstraintPresentation] = {
    presentation.value: presentation for presentation in (*_EDITABLE, _DEADLINE)
}


def coerce_constraint_type(value: ConstraintType | str | None) -> ConstraintType | None:
    """"" / None both mean ASAP -> None, matching Task.constraint_type's
    own normalization (domain/tasks/task.py). Raises ValueError for
    anything else unrecognized -- callers at a real mutation boundary
    should let that fail closed, not swallow it (see the audit's §43
    "invalid combinations" finding)."""
    if value is None or value == "":
        return None
    if isinstance(value, ConstraintType):
        return value
    return ConstraintType(str(value).strip())


def constraint_presentation(value: ConstraintType | str | None) -> ConstraintPresentation:
    """The one place any consumer (desktop serializer, QML presenter,
    Task editor option list) goes to turn a constraint value into
    something a user should see. Never title-case or hand-format a raw
    enum value anywhere else."""
    if value is None:
        return _ASAP
    if isinstance(value, ConstraintType):
        resolved = value
    else:
        resolved = ConstraintType(str(value))
    return _BY_VALUE[resolved]


__all__ = [
    "CATEGORY_DATE_BOUNDARY",
    "CATEGORY_FIXED_DATE",
    "CATEGORY_FLEXIBLE",
    "ConstraintPresentation",
    "EDITABLE_CONSTRAINT_OPTIONS",
    "coerce_constraint_type",
    "constraint_presentation",
]
