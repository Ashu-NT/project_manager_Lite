from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class TaskImportCapabilities:
    lookup: TaskLookupQueryHandler
    lifecycle: TaskLifecycleCommandHandler
    hierarchy: TaskHierarchyCommandHandler
    progress: TaskProgressCommandHandler
