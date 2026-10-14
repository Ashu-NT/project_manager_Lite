from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.resources.capacity.task_assignment_capacity_service import (
    TaskAssignmentCapacityFact,
)
from src.core.modules.project_management.application.scheduling.models.leveling import (
    LevelingProposal,
)
from src.core.modules.project_management.application.tasks.commands.approved_schedule_change import (
    ApprovedScheduleChangeHandler,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentActionContext,
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.deletion import (
    TaskDeletionCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.dependency import (
    TaskDependencyCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy import (
    TaskHierarchyCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.lifecycle import (
    TaskLifecycleCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.progress import (
    TaskProgressCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.resource_leveling_apply import (
    ResourceLevelingCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.scheduling_constraint import (
    TaskSchedulingConstraintHandler,
)
from src.core.modules.project_management.application.tasks.queries.dependency_query import (
    TaskDependencyQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.hierarchy_query import (
    TaskHierarchyQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_detail_page import (
    TaskDetailPageQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)
from src.core.modules.project_management.application.tasks.task_unit_of_work_scope import (
    TaskUowScope,
)
from src.core.modules.project_management.contracts.ports.scheduling.schedule_change import (
    AppliedTaskScheduleChange,
    ApprovedTaskScheduleChange,
)
from src.core.modules.project_management.domain.enums import (
    ConstraintType,
    DependencyType,
    TaskStatus,
)
from src.core.modules.project_management.domain.tasks.hierarchy import (
    TaskHierarchyNode,
    TaskHierarchyRollup,
)
from src.core.modules.project_management.domain.tasks.task import (
    Task,
    TaskAssignment,
    TaskDependency,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


class TaskService(
    ProjectManagementModuleGuardMixin,
):
    """Task application service orchestrator."""

    def __init__(
        self,
        user_session: UserSessionContext | None = None,
        module_catalog_service=None,
        *,
        detail_query_handler: TaskDetailPageQueryHandler,
        lookup_query_handler: TaskLookupQueryHandler,
        hierarchy_query_handler: TaskHierarchyQueryHandler,
        task_uow_scope: TaskUowScope,
        deletion_handler: TaskDeletionCommandHandler,
        progress_handler: TaskProgressCommandHandler,
        approved_schedule_change_handler: ApprovedScheduleChangeHandler,
        hierarchy_command_handler: TaskHierarchyCommandHandler,
        scheduling_constraint_handler: TaskSchedulingConstraintHandler,
        resource_leveling_handler: ResourceLevelingCommandHandler,
        lifecycle_handler: TaskLifecycleCommandHandler,
        dependency_command_handler: TaskDependencyCommandHandler,
        dependency_query_handler: TaskDependencyQueryHandler,
        assignment_handler: TaskAssignmentCommandHandler,
    ):
        self._user_session: UserSessionContext | None = user_session
        self._module_catalog_service = module_catalog_service
        self._detail_query = detail_query_handler
        self._lookup_query = lookup_query_handler
        self._hierarchy_query = hierarchy_query_handler
        self._task_uow_scope = task_uow_scope
        self._deletion_handler = deletion_handler
        self._progress_handler = progress_handler
        self._approved_schedule_change_handler = approved_schedule_change_handler
        self._hierarchy_command_handler = hierarchy_command_handler
        self._scheduling_constraint_handler = scheduling_constraint_handler
        self._resource_leveling_handler = resource_leveling_handler
        self._lifecycle_handler = lifecycle_handler
        self._dependency_command_handler = dependency_command_handler
        self._dependency_query_handler = dependency_query_handler
        self._assignment_handler = assignment_handler

    def delete_task(self, task_id: str) -> None:
        self._deletion_handler.delete_task(task_id)

    def assign_resource(
        self, task_id: str, resource_id: str, allocation_percent: float = 100.0
    ) -> TaskAssignment:
        return self._assignment_handler.assign_resource(task_id, resource_id, allocation_percent)

    def assign_project_resource(
        self,
        task_id: str,
        project_resource_id: str,
        allocation_percent: float,
        *,
        allocated_planned_hours: Decimal = Decimal(0),
    ) -> TaskAssignment:
        return self._assignment_handler.assign_project_resource(
            task_id,
            project_resource_id,
            allocation_percent,
            allocated_planned_hours=allocated_planned_hours,
        )

    def unassign_resource(self, assignment_id: str) -> None:
        self._assignment_handler.unassign_resource(assignment_id)

    def list_assignments_for_task(self, task_id: str) -> list[TaskAssignment]:
        return self._assignment_handler.list_assignments_for_task(task_id)

    def set_assignment_allocation(
        self, assignment_id: str, allocation_percent: float, *, expected_version: int
    ) -> TaskAssignment:
        return self._assignment_handler.set_assignment_allocation(
            assignment_id, allocation_percent, expected_version=expected_version
        )

    def update_assignment_planned_hours(
        self,
        assignment_id: str,
        *,
        allocated_planned_hours: Decimal,
        expected_assignment_version: int,
        expected_project_resource_version: int,
    ) -> TaskAssignment:
        return self._assignment_handler.update_assignment_planned_hours(
            assignment_id,
            allocated_planned_hours=allocated_planned_hours,
            expected_assignment_version=expected_assignment_version,
            expected_project_resource_version=expected_project_resource_version,
        )

    def preview_assignment_capacity(
        self,
        task_id: str,
        resource_id: str,
        *,
        proposed_allocation_percent: float = 100.0,
        exclude_assignment_id: str | None = None,
    ) -> TaskAssignmentCapacityFact | None:
        return self._assignment_handler.preview_assignment_capacity(
            task_id,
            resource_id,
            proposed_allocation_percent=proposed_allocation_percent,
            exclude_assignment_id=exclude_assignment_id,
        )

    def get_assignment_action_context(
        self, assignment_id: str
    ) -> TaskAssignmentActionContext:
        return self._assignment_handler.get_assignment_action_context(assignment_id)

    def accept_assignment(self, assignment_id: str) -> TaskAssignment:
        return self._assignment_handler.accept_assignment(assignment_id)

    def decline_assignment(
        self, assignment_id: str, reason: str | None = None
    ) -> TaskAssignment:
        return self._assignment_handler.decline_assignment(assignment_id, reason)

    def get_dependency(self, dep_id: str) -> TaskDependency | None:
        return self._dependency_query_handler.get_dependency(dep_id)

    def list_dependencies_for_task(self, task_id: str) -> list[TaskDependency]:
        return self._dependency_query_handler.list_dependencies_for_task(task_id)

    def list_dependencies_for_project(self, project_id: str) -> list[TaskDependency]:
        return self._dependency_query_handler.list_dependencies_for_project(project_id)

    def add_dependency(
        self,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
    ) -> TaskDependency:
        return self._dependency_command_handler.add_dependency(
            predecessor_id, successor_id, dependency_type, lag_days
        )

    def remove_dependency(self, dep_id: str) -> None:
        self._dependency_command_handler.remove_dependency(dep_id)

    def update_dependency(
        self,
        dep_id: str,
        *,
        dependency_type: DependencyType | None = None,
        lag_days: int | None = None,
        expected_version: int | None = None,
    ) -> TaskDependency:
        return self._dependency_command_handler.update_dependency(
            dep_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            expected_version=expected_version,
        )

    def _apply_dependency_add_decision(
        self,
        *,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType,
        lag_days: int,
    ) -> TaskDependency:
        return self._dependency_command_handler._apply_dependency_add_decision(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )

    def _apply_dependency_remove_decision(self, *, dependency_id: str) -> None:
        self._dependency_command_handler._apply_dependency_remove_decision(
            dependency_id=dependency_id
        )

    def _apply_dependency_update_decision(
        self,
        *,
        dependency_id: str,
        dependency_type: DependencyType,
        lag_days: int,
        expected_version: int | None = None,
    ) -> TaskDependency:
        return self._dependency_command_handler._apply_dependency_update_decision(
            dependency_id=dependency_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            expected_version=expected_version,
        )

    def create_task(
        self,
        project_id: str,
        name: str,
        description: str = "",
        start_date: date | None = None,
        duration_days: int | None = None,
        status: TaskStatus = TaskStatus.TODO,
        priority: int = 0,
        deadline: date | None = None,
        code: str = "",
        parent_task_id: str | None = None,
        wbs_code: str = "",
        sort_order: int | None = None,
        is_milestone: bool = False,
        constraint_type: ConstraintType | None = None,
        constraint_date: date | None = None,
    ) -> Task:
        return self._lifecycle_handler.create_task(
            project_id,
            name,
            description=description,
            start_date=start_date,
            duration_days=duration_days,
            status=status,
            priority=priority,
            deadline=deadline,
            code=code,
            parent_task_id=parent_task_id,
            wbs_code=wbs_code,
            sort_order=sort_order,
            is_milestone=is_milestone,
            constraint_type=constraint_type,
            constraint_date=constraint_date,
        )

    def update_task(
        self,
        task_id: str,
        name: str | None = None,
        description: str | None = None,
        start_date: date | None = None,
        duration_days: int | None = None,
        status: TaskStatus | None = None,
        priority: int | None = None,
        deadline: date | None = None,
        expected_version: int | None = None,
        code: str | None = None,
        is_milestone: bool | None = None,
    ) -> Task:
        return self._lifecycle_handler.update_task(
            task_id,
            name=name,
            description=description,
            start_date=start_date,
            duration_days=duration_days,
            status=status,
            priority=priority,
            deadline=deadline,
            expected_version=expected_version,
            code=code,
            is_milestone=is_milestone,
        )

    def update_task_scheduling_constraint(
        self,
        task_id: str,
        *,
        constraint_type: ConstraintType | None,
        constraint_date: date | None,
        expected_version: int | None = None,
    ) -> Task:
        return self._scheduling_constraint_handler.update_task_scheduling_constraint(
            task_id,
            constraint_type=constraint_type,
            constraint_date=constraint_date,
            expected_version=expected_version,
        )

    def _apply_task_scheduling_constraint_decision(
        self,
        *,
        task_id: str,
        constraint_type: ConstraintType | None,
        constraint_date: date | None,
        expected_version: int | None = None,
    ) -> Task:
        return self._scheduling_constraint_handler._apply_task_scheduling_constraint_decision(
            task_id=task_id,
            constraint_type=constraint_type,
            constraint_date=constraint_date,
            expected_version=expected_version,
        )

    def build_resource_leveling_preview(self, project_id: str) -> LevelingProposal | None:
        return self._resource_leveling_handler.build_resource_leveling_preview(project_id)

    def apply_resource_leveling_plan(
        self, project_id: str, proposal: LevelingProposal
    ) -> list[Task]:
        return self._resource_leveling_handler.apply_resource_leveling_plan(
            project_id, proposal
        )

    def _apply_resource_leveling_plan_decision(
        self, *, project_id: str, moves: list[dict], schedule_fingerprint: str
    ) -> list[Task]:
        return self._resource_leveling_handler._apply_resource_leveling_plan_decision(
            project_id=project_id,
            moves=moves,
            schedule_fingerprint=schedule_fingerprint,
        )

    def _validate_approved_schedule_changes(
        self, changes: list[ApprovedTaskScheduleChange]
    ) -> list[tuple[ApprovedTaskScheduleChange, Task]]:
        return self._approved_schedule_change_handler._validate_approved_schedule_changes(
            changes
        )

    def _apply_approved_schedule_changes(
        self, changes: list[ApprovedTaskScheduleChange], *, actor_id: str
    ) -> list[AppliedTaskScheduleChange]:
        return self._approved_schedule_change_handler._apply_approved_schedule_changes(
            changes, actor_id=actor_id
        )

    def delete_tasks(self, task_ids: tuple[str, ...]) -> tuple[str, ...]:
        return self._deletion_handler.delete_tasks(task_ids)

    def move_task(
        self,
        task_id: str,
        *,
        parent_task_id: str | None,
        wbs_code: str | None = None,
        sort_order: int | None = None,
        expected_version: int | None = None,
    ) -> Task:
        return self._hierarchy_command_handler.move_task(
            task_id,
            parent_task_id=parent_task_id,
            wbs_code=wbs_code,
            sort_order=sort_order,
            expected_version=expected_version,
        )

    def recode_task(
        self, task_id: str, wbs_code: str, *, expected_version: int | None = None
    ) -> Task:
        return self._hierarchy_command_handler.recode_task(
            task_id, wbs_code, expected_version=expected_version
        )

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        self._progress_handler.set_status(task_id, status)

    def set_tasks_status(
        self,
        task_ids: tuple[str, ...],
        status: TaskStatus,
        *,
        reopen_percent_complete: float | None = None,
    ) -> list[Task]:
        return self._progress_handler.set_tasks_status(
            task_ids, status, reopen_percent_complete=reopen_percent_complete
        )

    def update_progress(
        self,
        task_id: str,
        percent_complete: float | None = None,
        actual_start: date | None = None,
        actual_end: date | None = None,
        status: TaskStatus | None = None,
        expected_version: int | None = None,
    ) -> Task:
        return self._progress_handler.update_progress(
            task_id,
            percent_complete=percent_complete,
            actual_start=actual_start,
            actual_end=actual_end,
            status=status,
            expected_version=expected_version,
        )

    def get_task(self, task_id: str) -> Task | None:
        return self._detail_query.get_task(task_id)

    def list_task_hierarchy(self, project_id: str) -> list[TaskHierarchyNode]:
        return self._hierarchy_query.list_task_hierarchy(project_id)

    def list_leaf_tasks_for_project(self, project_id: str) -> list[Task]:
        return self._hierarchy_query.list_leaf_tasks_for_project(project_id)

    def get_task_hierarchy_rollup(self, task_id: str) -> TaskHierarchyRollup:
        return self._hierarchy_query.get_task_hierarchy_rollup(task_id)

    def list_task_hierarchy_rollups(
        self, project_id: str
    ) -> dict[str, TaskHierarchyRollup]:
        return self._hierarchy_query.list_task_hierarchy_rollups(project_id)

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return self._lookup_query.list_tasks_for_project(project_id)

    def _take_pending_task_events(self) -> tuple:
        return self._task_uow_scope.take_pending_events()

    def consume_last_overallocation_warning(self) -> str | None:
        return self._assignment_handler.consume_last_overallocation_warning()

    def consume_last_skill_violation_warning(self) -> str | None:
        return self._assignment_handler.consume_last_skill_violation_warning()


__all__ = ["TaskService"]
