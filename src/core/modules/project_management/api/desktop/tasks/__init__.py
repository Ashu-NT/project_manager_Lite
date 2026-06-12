from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.api import (
    ProjectManagementTasksDesktopApi,
)
from src.core.modules.project_management.api.desktop.tasks.commands.assignment_commands import (
    TaskAssignmentAllocationCommand,
    TaskAssignmentCreateCommand,
    TaskAssignmentHoursCommand,
)
from src.core.modules.project_management.api.desktop.tasks.commands.bulk_commands import (
    TaskBulkStatusCommand,
)
from src.core.modules.project_management.api.desktop.tasks.commands.dependency_commands import (
    TaskDependencyCreateCommand,
    TaskDependencyUpdateCommand,
)
from src.core.modules.project_management.api.desktop.tasks.commands.reservation_commands import (
    TaskReservationCreateCommand,
)
from src.core.modules.project_management.api.desktop.tasks.commands.task_commands import (
    TaskCreateCommand,
    TaskProgressCommand,
    TaskUpdateCommand,
)
from src.core.modules.project_management.api.desktop.tasks.factories.tasks_api_factory import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.api.desktop.tasks.models.assignment import (
    TaskAssignmentDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.dependency import (
    TaskDependencyDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.options import (
    TaskDependencyTypeDescriptor,
    TaskProjectOptionDescriptor,
    TaskProjectResourceOptionDescriptor,
    TaskStatusDescriptor,
)
from src.core.modules.project_management.api.desktop.tasks.models.reservation import (
    TaskMaterialDemandSummary,
    TaskReservationDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.skill import (
    TaskSkillRequirementDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.task import TaskDesktopDto
from src.core.modules.project_management.api.desktop.tasks.models.validation import (
    AssignmentPreviewDesktopDto,
    AssignmentValidationDesktopDto,
)


__all__ = [
    "AssignmentPreviewDesktopDto",
    "AssignmentValidationDesktopDto",
    "ProjectManagementTasksDesktopApi",
    "TaskAssignmentAllocationCommand",
    "TaskAssignmentCreateCommand",
    "TaskAssignmentDesktopDto",
    "TaskAssignmentHoursCommand",
    "TaskBulkStatusCommand",
    "TaskCreateCommand",
    "TaskDependencyCreateCommand",
    "TaskDependencyDesktopDto",
    "TaskDependencyTypeDescriptor",
    "TaskDependencyUpdateCommand",
    "TaskDesktopDto",
    "TaskMaterialDemandSummary",
    "TaskProgressCommand",
    "TaskProjectOptionDescriptor",
    "TaskProjectResourceOptionDescriptor",
    "TaskReservationCreateCommand",
    "TaskReservationDesktopDto",
    "TaskSkillRequirementDesktopDto",
    "TaskStatusDescriptor",
    "TaskUpdateCommand",
    "build_project_management_tasks_desktop_api",
]
