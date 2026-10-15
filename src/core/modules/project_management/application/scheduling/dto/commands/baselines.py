from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class SchedulingBaselineCreateCommand:
    project_id: str
    name: str = "Baseline"
    rate_as_of: date = field(default_factory=date.today)


@dataclass(frozen=True)
class SchedulingBaselineDeleteCommand:
    baseline_id: str


@dataclass(frozen=True)
class SchedulingBaselineSubmitCommand:
    baseline_id: str
    submitted_by: str = "system"
    notes: str = ""


@dataclass(frozen=True)
class SchedulingBaselineApproveCommand:
    baseline_id: str
    approved_by: str = "system"
    notes: str = ""


@dataclass(frozen=True)
class SchedulingBaselineRejectCommand:
    baseline_id: str
    notes: str = ""
