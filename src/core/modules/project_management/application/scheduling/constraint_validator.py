from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict, List, Optional

from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.application.scheduling.models import CPMTaskInfo


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
class ConstraintValidationResult:
    violations: List[ConstraintViolation]

    @property
    def is_valid(self) -> bool:
        return len(self.violations) == 0

    @property
    def hard_violations(self) -> List[ConstraintViolation]:
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
    def soft_violations(self) -> List[ConstraintViolation]:
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
        tasks_by_id: Dict[str, Task],
        cpm_result: Dict[str, CPMTaskInfo],
    ) -> ConstraintValidationResult:
        violations: List[ConstraintViolation] = []
        for task_id, task in tasks_by_id.items():
            info = cpm_result.get(task_id)
            if info is None:
                continue
            violations.extend(self._check_task(task, info))
        return ConstraintValidationResult(violations=violations)

    # ── per-task checks ─────────────────────────────────────────────────────

    def _check_task(self, task: Task, info: CPMTaskInfo) -> List[ConstraintViolation]:
        violations: List[ConstraintViolation] = []
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

    def _constraint_type(self, task: Task) -> Optional[ConstraintType]:
        raw = getattr(task, "constraint_type", None)
        if raw is None:
            return None
        if isinstance(raw, ConstraintType):
            return raw
        try:
            return ConstraintType(str(raw))
        except ValueError:
            return None

    def _constraint_date(self, task: Task) -> Optional[date]:
        return getattr(task, "constraint_date", None)


__all__ = [
    "ConstraintType",
    "ConstraintViolation",
    "ConstraintValidationResult",
    "ConstraintValidator",
]
