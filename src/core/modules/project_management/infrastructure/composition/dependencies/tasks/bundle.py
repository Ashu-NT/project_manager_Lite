from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentCommandHandler,
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
    lookup: TaskLookupQueryHandler
    workspace: TaskWorkspacePageQueryHandler
    assignment: TaskAssignmentCommandHandler
    lifecycle: TaskLifecycleCommandHandler
    hierarchy: TaskHierarchyCommandHandler
    progress: TaskProgressCommandHandler
