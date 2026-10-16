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


from src.core.modules.project_management.application.tasks.dto.responses.task import (
    TaskResponseDto,
)
from src.core.modules.project_management.application.tasks.mappers.task import map_task


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

    def create_task(self, command: TaskCreateCommand) -> TaskResponseDto:
        status = TaskStatus.TODO
        priority = command.priority if command.priority is not None else 0
        constraint_type = normalize_constraint_type(command.constraint_type)
        require_permission(self._user_session, "task.manage", operation_label="create task")
        require_project_permission(
            self._user_session,
            command.project_id,
            "task.manage",
            operation_label="create task",
        )
        task = Task.create(
            project_id=command.project_id,
            name=command.name,
            description=command.description,
            start_date=command.start_date,
            duration_days=command.duration_days,
            status=status,
            priority=priority,
            deadline=command.deadline,
            is_milestone=command.is_milestone,
            constraint_type=constraint_type,
            constraint_date=command.constraint_date,
        )
        self._scheduling_constraint_handler._validate_constraint_date_is_working_day(task)
        task.code = self._code_policy.resolve_task_code(command.code, command.project_id, task.name)
        task = self._hierarchy_policy._prepare_new_task_hierarchy(
            task,
            parent_task_id=command.parent_task_id,
            wbs_code=command.wbs_code,
            sort_order=command.sort_order,
        )
        # task.duration_days, not the raw duration_days param -- Task's own
        # model validator normalizes it to 0 for a milestone, and end_date
        # must stay consistent with whatever duration actually landed.
        if command.start_date and task.duration_days is not None:
            task.end_date = self._work_calendar_engine.add_working_days(
                command.start_date, int(task.duration_days)
            )

        self._validation_policy.validate_task_within_project_dates(
            command.project_id, task.start_date, task.end_date
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
                    workspace_id=command.project_id,
                    details={"name": task.name},
                    commit=False,
                )
                uow.record_event(
                    TaskCreated(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=command.project_id,
                        task_id=task.id,
                        occurred_at=datetime.now(UTC),
                    )
                )
                uow.commit()
            logger.info("Created task %s - %s for project %s", task.id, task.name, command.project_id)
            desired_status = task_status(command.status)
            if desired_status != task.status:
                changed = self._progress_handler._set_tasks_status_entities(
                    TaskBulkStatusCommand((task.id,), desired_status.value)
                )
                task = changed[0] if changed else task
            return map_task(task, project_name="")
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

    def update_task(self, command: TaskUpdateCommand) -> TaskResponseDto:
        desired_status = task_status(command.status)
        status = None
        require_permission(self._user_session, "task.manage", operation_label="update task")
        task = self._task_repo.get(command.task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.manage",
            operation_label="update task",
        )
        if command.expected_version is not None and task.version != command.expected_version:
            raise ConcurrencyError(
                "Task changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if self._task_repo.list_children(task.project_id, task.id):
            schedule_changed = (
                (command.start_date is not None and command.start_date != task.start_date)
                or (command.duration_days is not None and command.duration_days != task.duration_days)
                or (status is not None and status != task.status)
            )
            if schedule_changed:
                raise BusinessRuleError(
                    "Summary task schedule and status are rolled up from execution leaves.",
                    code="TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN",
                )

        next_name = task.name if command.name is None else command.name
        next_is_milestone = task.is_milestone if command.is_milestone is None else command.is_milestone
        next_duration_days = task.duration_days if command.duration_days is None else command.duration_days
        if next_is_milestone:
            # Normalized here, not left to Task's validator: end_date below is computed
            # from next_duration_days before replace() runs.
            next_duration_days = 0
        next_start_date = task.start_date if command.start_date is None else command.start_date
        next_end_date = task.end_date
        if (command.start_date is not None or command.duration_days is not None or command.is_milestone is not None) and (
            next_start_date and next_duration_days is not None
        ):
            next_end_date = self._work_calendar_engine.add_working_days(
                next_start_date,
                int(next_duration_days),
            )

        next_code = task.code
        if command.code is not None and command.code.strip():
            next_code = self._code_policy.resolve_task_code(
                command.code,
                task.project_id,
                next_name,
                exclude_id=task.id,
            )

        candidate = replace(
            task,
            name=next_name,
            description=task.description if command.description is None else command.description,
            start_date=next_start_date,
            end_date=next_end_date,
            duration_days=next_duration_days,
            status=task.status if status is None else status,
            priority=task.priority if command.priority is None else command.priority,
            deadline=task.deadline if command.deadline is None else command.deadline,
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
            changed = self._progress_handler._set_tasks_status_entities(
                TaskBulkStatusCommand((candidate.id,), desired_status.value)
            )
            candidate = changed[0] if changed else candidate
        return map_task(candidate, project_name="")

__all__ = ["TaskLifecycleCommandHandler"]
