from __future__ import annotations

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.application.scheduling.models.cpm import CPMTaskInfo


class ConstraintType(str, Enum):
    MUST_START_ON = "must_start_on"
    MUST_FINISH_ON = "must_finish_on"
    START_NO_EARLIER_THAN = "start_no_earlier_than"
    START_NO_LATER_THAN = "start_no_later_than"
    FINISH_NO_EARLIER_THAN = "finish_no_earlier_than"
    FINISH_NO_LATER_THAN = "finish_no_later_than"
    DEADLINE = "deadline"


@dataclass
class ConstraintViolation:
    task_id: str
    task_name: str
    constraint_type: ConstraintType
    constraint_date: date
    computed_date: date
    message: str
    overrun_working_days: int


@dataclass
class DependencyConstraintConflict:
    """A hard scheduling constraint (Must Start On / Must Finish On)
    silently overrode what the task's incoming TaskDependency edges
    required. Non-blocking -- this is a reported fact, not a raised error;
    the schedule still uses the constraint-driven date (see
    SchedulingEngine._apply_scheduling_constraints), but the conflict is no
    longer invisible. 
    """

    task_id: str
    task_name: str
    constraint_type: ConstraintType
    constraint_date: date
    dependency_required_date: date
    direction: str  # "start" or "finish"
    # Positive: the constraint pulled the task EARLIER than the dependency
    # required (dependency_required_date is later than constraint_date).
    # Negative: the constraint pushed the task LATER than the dependency
    # required.
    difference_working_days: int
    code: str = "DEPENDENCY_CONSTRAINT_CONFLICT"


@dataclass
class ConstraintValidationResult:
    violations: list[ConstraintViolation]
    dependency_conflicts: list[DependencyConstraintConflict] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.violations) == 0

    @property
    def hard_violations(self) -> list[ConstraintViolation]:
        """Violations that represent firm date mismatches (MSO / MFO / hard limits)."""
        hard = {
            ConstraintType.MUST_START_ON,
            ConstraintType.MUST_FINISH_ON,
            ConstraintType.START_NO_LATER_THAN,
            ConstraintType.FINISH_NO_LATER_THAN,
            ConstraintType.DEADLINE,
        }
        return [v for v in self.violations if v.constraint_type in hard]

    @property
    def soft_violations(self) -> list[ConstraintViolation]:
        soft = {
            ConstraintType.START_NO_EARLIER_THAN,
            ConstraintType.FINISH_NO_EARLIER_THAN,
        }
        return [v for v in self.violations if v.constraint_type in soft]


class ConstraintValidator:
    """
    Validates computed CPM dates against the hard and soft scheduling constraints
    stored on each Task.

    Tasks may carry constraint metadata via duck-typed attributes:
        constraint_type: ConstraintType | str | None
        constraint_date: date | None
    Deadline is read from task.deadline (already in the domain model).

    Step 3 (enterprise calendar / constraint hardening) will wire these fields
    into the DB model and migration.  This validator works with or without them.
    """

    def __init__(self, calendar: CalendarProtocol) -> None:
        self._calendar = calendar

    def validate(
        self,
        tasks_by_id: dict[str, Task],
        cpm_result: dict[str, CPMTaskInfo],
    ) -> ConstraintValidationResult:
        violations: list[ConstraintViolation] = []
        dependency_conflicts: list[DependencyConstraintConflict] = []
        for task_id, task in tasks_by_id.items():
            info = cpm_result.get(task_id)
            if info is None:
                continue
            violations.extend(self._check_task(task, info))
            dependency_conflicts.extend(self._check_dependency_conflict(task, info))
        return ConstraintValidationResult(violations=violations, dependency_conflicts=dependency_conflicts)

    # ── per-task checks ─────────────────────────────────────────────────────

    def _check_dependency_conflict(
        self, task: Task, info: CPMTaskInfo
    ) -> list[DependencyConstraintConflict]:
        """Report when a hard MUST_START_ON/MUST_FINISH_ON constraint
        overrode what the task's incoming dependencies alone required.

        Reads ``CPMTaskInfo.dependency_implied_start/finish``, captured by
        the scheduling engine BEFORE constraints were applied (Phase F) --
        this is what makes the comparison possible; comparing against the
        already-overridden ``earliest_start``/``earliest_finish`` (as the
        MSO/MFO violation check above does) can never detect this, because
        by the time this validator runs, the override has already happened.
        """
        ct = self._constraint_type(task)
        cd = self._constraint_date(task)
        if ct is None or cd is None:
            return []

        if ct == ConstraintType.MUST_START_ON and info.dependency_implied_start is not None:
            required = info.dependency_implied_start
            if required != cd:
                return [self._dependency_conflict(task, ct, cd, required, "start")]

        if ct == ConstraintType.MUST_FINISH_ON and info.dependency_implied_finish is not None:
            required = info.dependency_implied_finish
            if required != cd:
                return [self._dependency_conflict(task, ct, cd, required, "finish")]

        return []

    def _dependency_conflict(
        self,
        task: Task,
        ct: ConstraintType,
        constraint_date: date,
        dependency_required_date: date,
        direction: str,
    ) -> DependencyConstraintConflict:
        if dependency_required_date > constraint_date:
            diff = self._calendar.working_days_between(constraint_date, dependency_required_date) - 1
        else:
            diff = -(self._calendar.working_days_between(dependency_required_date, constraint_date) - 1)
        return DependencyConstraintConflict(
            task_id=task.id,
            task_name=task.name,
            constraint_type=ct,
            constraint_date=constraint_date,
            dependency_required_date=dependency_required_date,
            direction=direction,
            difference_working_days=diff,
        )

    def _check_task(self, task: Task, info: CPMTaskInfo) -> list[ConstraintViolation]:
        violations: list[ConstraintViolation] = []
        ct = self._constraint_type(task)
        cd = self._constraint_date(task)

        if ct is not None and cd is not None:
            es = info.earliest_start
            ef = info.earliest_finish

            if ct == ConstraintType.MUST_START_ON and es is not None and es != cd:
                violations.append(self._violation(task, ct, cd, es, "must start on"))

            elif ct == ConstraintType.MUST_FINISH_ON and ef is not None and ef != cd:
                violations.append(self._violation(task, ct, cd, ef, "must finish on"))

            elif ct == ConstraintType.START_NO_EARLIER_THAN and es is not None and es < cd:
                violations.append(self._violation(task, ct, cd, es, "cannot start before"))

            elif ct == ConstraintType.START_NO_LATER_THAN and es is not None and es > cd:
                violations.append(self._violation(task, ct, cd, es, "must start no later than"))

            elif ct == ConstraintType.FINISH_NO_EARLIER_THAN and ef is not None and ef < cd:
                violations.append(self._violation(task, ct, cd, ef, "cannot finish before"))

            elif ct == ConstraintType.FINISH_NO_LATER_THAN and ef is not None and ef > cd:
                violations.append(self._violation(task, ct, cd, ef, "must finish no later than"))

        # Deadline is always checked independently of constraint_type
        deadline = getattr(task, "deadline", None)
        ef = info.earliest_finish
        if deadline and ef and ef > deadline:
            violations.append(self._violation(task, ConstraintType.DEADLINE, deadline, ef, "exceeds deadline"))

        return violations

    def _violation(
        self,
        task: Task,
        ct: ConstraintType,
        constraint_date: date,
        computed_date: date,
        label: str,
    ) -> ConstraintViolation:
        if computed_date > constraint_date:
            overrun = max(0, self._calendar.working_days_between(constraint_date, computed_date) - 1)
        else:
            overrun = max(0, self._calendar.working_days_between(computed_date, constraint_date) - 1)
        return ConstraintViolation(
            task_id=task.id,
            task_name=task.name,
            constraint_type=ct,
            constraint_date=constraint_date,
            computed_date=computed_date,
            message=f"Task '{task.name}' {label} {constraint_date.isoformat()} but computed {computed_date.isoformat()}",
            overrun_working_days=overrun,
        )

    # ── duck-typed attribute readers ────────────────────────────────────────

    def _constraint_type(self, task: Task) -> ConstraintType | None:
        raw = getattr(task, "constraint_type", None)
        if raw is None:
            return None
        if isinstance(raw, ConstraintType):
            return raw
        try:
            return ConstraintType(str(raw))
        except ValueError:
            return None

    def _constraint_date(self, task: Task) -> date | None:
        return getattr(task, "constraint_date", None)


__all__ = [
    "ConstraintType",
    "ConstraintViolation",
    "ConstraintValidationResult",
    "ConstraintValidator",
    "DependencyConstraintConflict",
]
