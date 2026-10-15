from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.tasks._command_values import (
    constraint_type as normalize_constraint_type,
)
from src.core.modules.project_management.application.tasks._command_values import (
    task_status,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy_support import (
    TaskHierarchyPolicy,
)
from src.core.modules.project_management.application.tasks.commands.identity import (
    TaskCodePolicy,
)
from src.core.modules.project_management.application.tasks.commands.progress import (
    TaskProgressCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.scheduling_constraint import (
    TaskSchedulingConstraintHandler,
)
from src.core.modules.project_management.application.tasks.commands.validation import (
    TaskValidationPolicy,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_lifecycle import (
    TaskCreateCommand,
    TaskUpdateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_progress import (
    TaskBulkStatusCommand,
)
from src.core.modules.project_management.application.tasks.task_events import (
    TaskCreated,
    TaskProfileUpdated,
    TaskStatusChanged,
)
from src.core.modules.project_management.application.tasks.task_unit_of_work_scope import (
    TaskUowScope,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    TaskRepository,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.activity import record_activity

logger = logging.getLogger(__name__)


class TaskLifecycleCommandHandler(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        *,
        module_catalog_service=None,
        task_repo: TaskRepository,
        work_calendar_engine: CalendarProtocol,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService,
        code_policy: TaskCodePolicy,
        hierarchy_policy: TaskHierarchyPolicy,
        validation_policy: TaskValidationPolicy,
        scheduling_constraint_handler: TaskSchedulingConstraintHandler,
        progress_handler: TaskProgressCommandHandler,
        uow_scope: TaskUowScope,
    ) -> None:
        self._module_catalog_service = module_catalog_service
        self._task_repo = task_repo
        self._work_calendar_engine = work_calendar_engine
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._code_policy = code_policy
        self._hierarchy_policy = hierarchy_policy
        self._validation_policy = validation_policy
        self._scheduling_constraint_handler = scheduling_constraint_handler
        self._progress_handler = progress_handler
        self._uow_scope = uow_scope

    def create_task(self, command: TaskCreateCommand) -> Task:
        project_id = command.project_id
        name = command.name
        description = command.description
        start_date = command.start_date
        duration_days = command.duration_days
        status = TaskStatus.TODO
        priority = command.priority if command.priority is not None else 0
        deadline = command.deadline
        code = command.code
        parent_task_id = command.parent_task_id
        wbs_code = command.wbs_code
        sort_order = command.sort_order
        is_milestone = command.is_milestone
        constraint_type = normalize_constraint_type(command.constraint_type)
        constraint_date = command.constraint_date
        require_permission(self._user_session, "task.manage", operation_label="create task")
        require_project_permission(
            self._user_session,
            project_id,
            "task.manage",
            operation_label="create task",
        )
        task = Task.create(
            project_id=project_id,
            name=name,
            description=description,
            start_date=start_date,
            duration_days=duration_days,
            status=status,
            priority=priority,
            deadline=deadline,
            is_milestone=is_milestone,
            constraint_type=constraint_type,
            constraint_date=constraint_date,
        )
        self._scheduling_constraint_handler._validate_constraint_date_is_working_day(task)
        task.code = self._code_policy.resolve_task_code(code, project_id, task.name)
        task = self._hierarchy_policy._prepare_new_task_hierarchy(
            task,
            parent_task_id=parent_task_id,
            wbs_code=wbs_code,
            sort_order=sort_order,
        )
        # task.duration_days, not the raw duration_days param -- Task's own
        # model validator normalizes it to 0 for a milestone, and end_date
        # must stay consistent with whatever duration actually landed.
        if start_date and task.duration_days is not None:
            task.end_date = self._work_calendar_engine.add_working_days(
                start_date, int(task.duration_days)
            )

        self._validation_policy.validate_task_within_project_dates(
            project_id, task.start_date, task.end_date
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="create task"
        )

        try:
            task = self._hierarchy_policy._resequence_for_new_task(task)
            with self._uow_scope.create() as uow:
                uow.tasks.add(task)
                record_activity(
                    uow,
                    action="task.create",
                    entity_type="task",
                    entity_id=task.id,
                    module="project_management",
                    workspace_id=project_id,
                    details={"name": task.name},
                    commit=False,
                )
                uow.record_event(
                    TaskCreated(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=project_id,
                        task_id=task.id,
                        occurred_at=datetime.now(UTC),
                    )
                )
                uow.commit()
            logger.info("Created task %s - %s for project %s", task.id, task.name, project_id)
            desired_status = task_status(command.status)
            if desired_status != task.status:
                changed = self._progress_handler.set_tasks_status(
                    TaskBulkStatusCommand((task.id,), desired_status.value)
                )
                task = changed[0] if changed else task
            return task
        except IntegrityError as exc:
            if self._code_policy.is_task_code_integrity_error(exc):
                self._code_policy.raise_task_code_duplicate(task.code, exc)
            if self._hierarchy_policy._is_task_wbs_integrity_error(exc):
                raise ValidationError(
                    "The WBS code or parent conflicts with another task.",
                    code="TASK_WBS_CONFLICT",
                ) from exc
            logger.error("Error creating task: %s", exc)
            raise
        except Exception as exc:
            logger.error("Error creating task: %s", exc)
            raise

    def update_task(self, command: TaskUpdateCommand) -> Task:
        desired_status = task_status(command.status)
        task_id = command.task_id
        name = command.name
        description = command.description
        start_date = command.start_date
        duration_days = command.duration_days
        status = None
        priority = command.priority
        deadline = command.deadline
        expected_version = command.expected_version
        code = command.code
        is_milestone = command.is_milestone
        require_permission(self._user_session, "task.manage", operation_label="update task")
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.manage",
            operation_label="update task",
        )
        if expected_version is not None and task.version != expected_version:
            raise ConcurrencyError(
                "Task changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if self._task_repo.list_children(task.project_id, task.id):
            schedule_changed = (
                (start_date is not None and start_date != task.start_date)
                or (duration_days is not None and duration_days != task.duration_days)
                or (status is not None and status != task.status)
            )
            if schedule_changed:
                raise BusinessRuleError(
                    "Summary task schedule and status are rolled up from execution leaves.",
                    code="TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN",
                )

        next_name = task.name if name is None else name
        next_is_milestone = task.is_milestone if is_milestone is None else is_milestone
        next_duration_days = task.duration_days if duration_days is None else duration_days
        if next_is_milestone:
            # Normalized here, not left to Task's validator: end_date below is computed
            # from next_duration_days before replace() runs.
            next_duration_days = 0
        next_start_date = task.start_date if start_date is None else start_date
        next_end_date = task.end_date
        if (start_date is not None or duration_days is not None or is_milestone is not None) and (
            next_start_date and next_duration_days is not None
        ):
            next_end_date = self._work_calendar_engine.add_working_days(
                next_start_date,
                int(next_duration_days),
            )

        next_code = task.code
        if code is not None and code.strip():
            next_code = self._code_policy.resolve_task_code(
                code,
                task.project_id,
                next_name,
                exclude_id=task.id,
            )

        candidate = replace(
            task,
            name=next_name,
            description=task.description if description is None else description,
            start_date=next_start_date,
            end_date=next_end_date,
            duration_days=next_duration_days,
            status=task.status if status is None else status,
            priority=task.priority if priority is None else priority,
            deadline=task.deadline if deadline is None else deadline,
            code=next_code,
            is_milestone=next_is_milestone,
        )

        self._validation_policy.validate_task_within_project_dates(
            candidate.project_id,
            candidate.start_date,
            candidate.end_date,
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="update task"
        )

        try:
            with self._uow_scope.create() as uow:
                uow.tasks.update(candidate)
                record_activity(
                    uow,
                    action="task.update",
                    entity_type="task",
                    entity_id=candidate.id,
                    module="project_management",
                    workspace_id=candidate.project_id,
                    details={"name": candidate.name, "status": candidate.status.value},
                    commit=False,
                )
                uow.record_event(
                    TaskProfileUpdated(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=candidate.project_id,
                        task_id=candidate.id,
                        occurred_at=datetime.now(UTC),
                    )
                )
                if status is not None and status != task.status:
                    uow.record_event(
                        TaskStatusChanged(
                            tenant_id=scope.tenant_id,
                            organization_id=scope.organization_id,
                            project_id=candidate.project_id,
                            task_id=candidate.id,
                            old_status=task.status.value,
                            new_status=candidate.status.value,
                            occurred_at=datetime.now(UTC),
                        )
                    )
                uow.commit()
        except IntegrityError as exc:
            if self._code_policy.is_task_code_integrity_error(exc):
                self._code_policy.raise_task_code_duplicate(candidate.code, exc)
            raise
        if desired_status != task.status:
            changed = self._progress_handler.set_tasks_status(
                TaskBulkStatusCommand((candidate.id,), desired_status.value)
            )
            candidate = changed[0] if changed else candidate
        return candidate

__all__ = ["TaskLifecycleCommandHandler"]
