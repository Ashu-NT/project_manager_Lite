"""Task queries."""

from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    DependencyDiagnostic,
    DependencyImpactRow,
    TaskDependencyDiagnosticsQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)

__all__ = [
    "DependencyDiagnostic",
    "DependencyImpactRow",
    "TaskDependencyDiagnosticsQueryHandler",
    "TaskLookupQueryHandler",
]
