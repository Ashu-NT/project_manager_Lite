from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.application.projects.service import (
    ProjectService,
)


@dataclass(frozen=True)
class ProjectComposition:
    service: ProjectService
    query: ProjectQueryHandler
