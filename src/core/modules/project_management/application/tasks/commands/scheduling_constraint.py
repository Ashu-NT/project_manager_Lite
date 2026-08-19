from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.domain.enums import ConstraintType
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.domain.approval.policy import is_governance_required
from src.core.shared.activity import record_activity
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    is_admin_session,
    require_permission,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.events.domain_events import domain_events


class TaskSchedulingConstraintMixin:
    """Governed Task scheduling-constraint mutation (MSO/MFO/SNET/SNLT/
    FNET/FNLT + clear-back-to-ASAP). Mirrors TaskDependencyMixin's
    request-time/apply-time governance shape (see
    docs/pm_modernization/R4_4_TASK_CONSTRAINT_CURRENT_STATE_AND_TARGET_GAPS.md
    §21/§28) -- separate from generic update_task rather than overloading
    it with raw dict semantics, matching how dependency mutations already
    get their own dedicated, explicitly-governed command shape.

    Task.deadline is intentionally NOT part of this command: it never
    drives CPM (validation-only, same as FINISH_NO_LATER_THAN) and stays
    on the plain update_task path -- see the implementation summary's
    "Deadline governance decision" for the explicit reasoning.
    """

    def update_task_scheduling_constraint(
        self,
        task_id: str,
        *,
        constraint_type: ConstraintType | None,
        constraint_date: date | None,
        expected_version: int | None = None,
    ) -> Task:
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        if expected_version is not None and task.version != expected_version:
            raise ConcurrencyError("Task was updated by another user.", code="STALE_WRITE")

        candidate = replace(task, constraint_type=constraint_type, constraint_date=constraint_date)
        self._validate_constraint_date_is_working_day(candidate)

        governed = (
            self._approval_service is not None
            and is_governance_required("task.constraint.update")
            and not is_admin_session(self._user_session)
        )
        if governed:
            require_permission(
                self._user_session, "approval.request", operation_label="request scheduling constraint change"
            )
            require_project_permission(
                self._user_session,
                task.project_id,
                "approval.request",
                operation_label="request scheduling constraint change",
            )
        else:
            require_permission(self._user_session, "task.manage", operation_label="update scheduling constraint")
            require_project_permission(
                self._user_session,
                task.project_id,
                "task.manage",
                operation_label="update scheduling constraint",
            )

        if governed:
            request = self._approval_service.request_change(
                request_type="task.constraint.update",
                entity_type="task",
                entity_id=task.id,
                project_id=task.project_id,
                payload={
                    "task_id": task.id,
                    "task_name": task.name,
                    "constraint_type": constraint_type.value if constraint_type is not None else None,
                    "constraint_date": constraint_date.isoformat() if constraint_date is not None else None,
                    # Version AT REQUEST TIME -- re-checked against
                    # whatever is current when this is finally applied,
                    # since approval can land long after the request.
                    "expected_version": task.version,
                },
            )
            raise BusinessRuleError(
                f"Approval required for scheduling constraint change. Request {request.id} created.",
                code="APPROVAL_REQUIRED",
            )

        return self._apply_task_scheduling_constraint_decision(
            task_id=task_id,
            constraint_type=constraint_type,
            constraint_date=constraint_date,
            expected_version=task.version,
            commit=True,
        )

    def _apply_task_scheduling_constraint_decision(
        self,
        *,
        task_id: str,
        constraint_type: ConstraintType | None,
        constraint_date: date | None,
        expected_version: int | None = None,
        commit: bool,
    ) -> Task:
        """Apply immediately (ungoverned path) or when an approved
        ``task.constraint.update`` request is finally applied. Re-fetches
        the CURRENT task and re-validates version/calendar rather than
        trusting request-time facts -- matching the TOCTOU fix already
        established for dependency mutations: real time (and possibly the
        task's version or calendar exceptions) may have passed since the
        original request was validated. ``expected_version`` is the
        version captured AT REQUEST TIME (governed path) or just-read
        (ungoverned path) -- not re-derived from the current row, or this
        check could never fire."""
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if expected_version is not None and task.version != expected_version:
            raise ConcurrencyError("Task was updated by another user.", code="STALE_WRITE")
        candidate = replace(task, constraint_type=constraint_type, constraint_date=constraint_date)
        self._validate_constraint_date_is_working_day(candidate)
        try:
            self._task_repo.update(candidate)
            # Same one-transaction mutate+recalculate flow every other
            # schedule-affecting task command uses (TaskScheduleSyncMixin)
            # -- if recalculation raises, the outer except below rolls
            # back the constraint write too; there is no separate
            # constraint scheduler.
            self._sync_project_schedule(candidate.project_id, commit=False)
            record_activity(
                self,
                action="task.constraint.update",
                entity_type="task",
                entity_id=candidate.id,
                module="project_management",
                workspace_id=candidate.project_id,
                details={
                    "constraint_type": constraint_type.value if constraint_type is not None else None,
                    "constraint_date": constraint_date.isoformat() if constraint_date is not None else None,
                },
                commit=False,
            )
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except Exception:
            if commit:
                self._session.rollback()
            raise
        if commit:
            domain_events.tasks_changed.emit(candidate.project_id)
        return self._task_repo.get(task_id)

    def _validate_constraint_date_is_working_day(self, candidate: Task) -> None:
        """Enterprise policy (not Mon-Fri): an explicit constraint date
        that isn't a working day under the AUTHORITATIVE project calendar
        is rejected outright, not silently snapped -- "Must Start On
        Saturday" quietly becoming Monday would change the user's
        explicit instruction without telling them."""
        if candidate.constraint_type is None or candidate.constraint_date is None:
            return
        scheduler = getattr(self, "_scheduling_engine", None)
        calendar = (
            scheduler.calendar_for_project(candidate.project_id)
            if scheduler is not None
            else self._work_calendar_engine
        )
        if calendar.is_working_day(candidate.constraint_date):
            return
        nearest = calendar.next_working_day(candidate.constraint_date, include_today=True)
        raise ValidationError(
            f"{candidate.constraint_date.isoformat()} is not a working day in this "
            f"project's calendar -- the nearest working day is {nearest.isoformat()}.",
            code="CONSTRAINT_DATE_NON_WORKING",
        )


__all__ = ["TaskSchedulingConstraintMixin"]
