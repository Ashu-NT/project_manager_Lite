from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.api import (
    ProjectManagementTasksDesktopApi,
)
from src.core.modules.project_management.api.desktop.tasks.factories.tasks_api_factory import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.api.desktop.tasks.models.assignment import (
    TaskAssignmentDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.dependency import (
    TaskDependencyDesktopDto,
    TaskDependencyImpactPreviewDesktopDto,
    TaskDependencyImpactRowDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.options import (
    TaskConstraintOptionDescriptor,
    TaskDependencyTypeDescriptor,
    TaskProjectOptionDescriptor,
    TaskProjectResourceOptionDescriptor,
    TaskStatusDescriptor,
)
from src.core.modules.project_management.api.desktop.tasks.models.skill import (
    TaskSkillRequirementDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.task import (
    TaskDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.time_summary import (
    TaskTimeEntriesPageDesktopDto,
    TaskTimeEntryDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.validation import (
    AssignmentPreviewDesktopDto,
    AssignmentValidationDesktopDto,
)

__all__ = [
    "AssignmentPreviewDesktopDto",
    "AssignmentValidationDesktopDto",
    "ProjectManagementTasksDesktopApi",
    "TaskAssignmentDesktopDto",
    "TaskConstraintOptionDescriptor",
    "TaskDependencyDesktopDto",
    "TaskDependencyImpactPreviewDesktopDto",
    "TaskDependencyImpactRowDesktopDto",
    "TaskDependencyTypeDescriptor",
    "TaskDesktopDto",
    "TaskProjectOptionDescriptor",
    "TaskProjectResourceOptionDescriptor",
    "TaskSkillRequirementDesktopDto",
    "TaskStatusDescriptor",
    "TaskTimeEntriesPageDesktopDto",
    "TaskTimeEntryDesktopDto",
    "build_project_management_tasks_desktop_api",
]
