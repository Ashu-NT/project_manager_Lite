from dataclasses import dataclass


@dataclass(frozen=True)
class SchedulingBaselineCreateCommand:
    project_id: str
    name: str = "Baseline"


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


__all__ = [
    "SchedulingBaselineApproveCommand",
    "SchedulingBaselineCreateCommand",
    "SchedulingBaselineRejectCommand",
    "SchedulingBaselineSubmitCommand",
]
