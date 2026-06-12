from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.api import (
    ProjectManagementTasksDesktopApi,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.modules.project_management.application.resources.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.resources.resource_availability_service import (
    ResourceAvailabilityService,
)
from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import (
    ScheduleChangeImpactService,
)
from src.core.modules.project_management.application.tasks import TaskService


def build_project_management_tasks_desktop_api(
    *,
    project_service: ProjectService | None = None,
    task_service: TaskService | None = None,
    project_resource_service: ProjectResourceService | None = None,
    resource_service: ResourceService | None = None,
    reservation_service: object | None = None,
    assignment_skill_validator: AssignmentSkillValidator | None = None,
    schedule_change_impact_service: ScheduleChangeImpactService | None = None,
    resource_availability_service: ResourceAvailabilityService | None = None,
) -> ProjectManagementTasksDesktopApi:
    return ProjectManagementTasksDesktopApi(
        project_service=project_service,
        task_service=task_service,
        project_resource_service=project_resource_service,
        resource_service=resource_service,
        reservation_service=reservation_service,
        assignment_skill_validator=assignment_skill_validator,
        schedule_change_impact_service=schedule_change_impact_service,
        resource_availability_service=resource_availability_service,
    )


__all__ = ["build_project_management_tasks_desktop_api"]
