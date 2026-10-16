from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.api import (
    ProjectManagementTasksDesktopApi,
)
from src.core.modules.project_management.api.desktop.tasks.factories.tasks_api_factory import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.api.desktop.tasks.models.options import (
    TaskConstraintOptionDescriptor,
    TaskDependencyTypeDescriptor,
    TaskProjectOptionDescriptor,
    TaskProjectResourceOptionDescriptor,
    TaskStatusDescriptor,
)

__all__ = [
    "ProjectManagementTasksDesktopApi",
    "TaskConstraintOptionDescriptor",
    "TaskDependencyTypeDescriptor",
    "TaskProjectOptionDescriptor",
    "TaskProjectResourceOptionDescriptor",
    "TaskStatusDescriptor",
    "build_project_management_tasks_desktop_api",
]
