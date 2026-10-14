from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.tasks import (
    ApprovedScheduleChangeHandler,
    ResourceLevelingCommandHandler,
    TaskDeletionCommandHandler,
    TaskDependencyCommandHandler,
    TaskDependencyQueryHandler,
    TaskHierarchyCommandHandler,
    TaskHierarchyQueryHandler,
    TaskLifecycleCommandHandler,
    TaskProgressCommandHandler,
    TaskSchedulingConstraintHandler,
    TaskUowScope,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.time_entries import (
    TaskTimeEntryHandler,
)
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    TaskDependencyDiagnosticsQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_detail_page import (
    TaskDetailPageQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_workspace_page import (
    TaskWorkspacePageQueryHandler,
)
from src.core.modules.project_management.application.tasks.service import TaskService


@dataclass(frozen=True)
class TaskComposition:
    service: TaskService
    hierarchy_query: TaskHierarchyQueryHandler
    deletion: TaskDeletionCommandHandler
    progress: TaskProgressCommandHandler
    schedule_changes: ApprovedScheduleChangeHandler
    hierarchy: TaskHierarchyCommandHandler
    constraints: TaskSchedulingConstraintHandler
    leveling: ResourceLevelingCommandHandler
    lifecycle: TaskLifecycleCommandHandler
    dependencies: TaskDependencyCommandHandler
    dependency_query: TaskDependencyQueryHandler
    uow_scope: TaskUowScope
    lookup: TaskLookupQueryHandler
    workspace: TaskWorkspacePageQueryHandler
    detail: TaskDetailPageQueryHandler
    dependency_diagnostics: TaskDependencyDiagnosticsQueryHandler
    assignment: TaskAssignmentCommandHandler
    time_entries: TaskTimeEntryHandler
