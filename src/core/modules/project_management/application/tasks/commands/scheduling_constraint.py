from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

from src.core.modules.project_management.application.tasks.commands.schedule_sync import (
    emit_cascade_schedule_changed,
)
from src.core.modules.project_management.application.tasks.task_events import (
    TaskScheduleChangeType,
    TaskScheduleChanged,
)
from src.core.modules.project_management.domain.enums import ConstraintType
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.domain.approval.policy import is_governance_required
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
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


class TaskSchedulingConstraintMixin:
    """Governed Task scheduling-constraint mutation (MSO/MFO/SNET/SNLT/
    FNET/FNLT + clear-back-to-ASAP). Mirrors TaskDependencyMixin's
    request-time/apply-time governance shape -- kept separate from generic
    update_task rather than overloading it with raw dict semantics.

    Task.deadline is intentionally NOT part of this command: it never
    drives CPM (validation-only, same as FINISH_NO_LATER_THAN) and stays
    on the plain update_task path.
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
        )

    def _apply_task_scheduling_constraint_decision(
        self,
        *,
        task_id: str,
        constraint_type: ConstraintType | None,
        constraint_date: date | None,
        expected_version: int | None = None,
    ) -> Task:
        """Apply immediately (ungoverned path) or when an approved
        ``task.constraint.update`` request is finally applied. Re-fetches
        the CURRENT task and re-validates version/calendar rather than
        trusting request-time facts, since real time (and possibly the
        task's version or calendar exceptions) may have passed.
        ``expected_version`` is the version captured at request time
        (governed path) or just-read (ungoverned path) -- not re-derived
        from the current row, or this check could never fire."""
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if expected_version is not None and task.version != expected_version:
            raise ConcurrencyError("Task was updated by another user.", code="STALE_WRITE")
        candidate = replace(task, constraint_type=constraint_type, constraint_date=constraint_date)
        self._validate_constraint_date_is_working_day(candidate)
        scope = self._active_task_scope(operation_label="update scheduling constraint")
        with self._task_uow() as uow:
            uow.tasks.update(candidate)
            # Same one-transaction mutate+recalculate flow every other
            # schedule-affecting task command uses (TaskScheduleSyncMixin)
            # -- if recalculation raises, the UoW context manager rolls
            # back the constraint write too; there is no separate
            # constraint scheduler.
            cascade_ids = self._sync_project_schedule(
                candidate.project_id, commit=False, exclude_task_ids=frozenset({candidate.id})
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="task",
                entity_id=candidate.id,
                module="project_management",
                organization_id=scope.organization_id,
                severity="low",
                metadata={
                    "action": "task.constraint.update",
                    "constraint_type": constraint_type.value if constraint_type is not None else None,
                },
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
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
            uow.record_event(
                TaskScheduleChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=candidate.project_id,
                    task_id=candidate.id,
                    change_type=TaskScheduleChangeType.CONSTRAINT_UPDATED,
                    occurred_at=datetime.now(timezone.utc),
                )
            )
            emit_cascade_schedule_changed(
                uow, scope=scope, project_id=candidate.project_id, changed_task_ids=cascade_ids
            )
            uow.commit()
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
