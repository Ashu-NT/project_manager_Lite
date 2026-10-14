from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.projects.commands.create import (
    ProjectCreateHandler,
)
from src.core.modules.project_management.application.projects.commands.deletion import (
    ProjectDeletionHandler,
)
from src.core.modules.project_management.application.projects.commands.status import (
    ProjectStatusHandler,
)
from src.core.modules.project_management.application.projects.commands.update import (
    ProjectUpdateHandler,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)


@dataclass(frozen=True)
class ProjectComposition:
    query: ProjectQueryHandler
    create: ProjectCreateHandler
    update: ProjectUpdateHandler
    status: ProjectStatusHandler
    deletion: ProjectDeletionHandler
