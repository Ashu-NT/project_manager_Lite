from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.api import (
    ProjectManagementTasksDesktopApi,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import (
    ScheduleChangeImpactService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    TaskDependencyDiagnosticsQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_detail_page import (
    TaskDetailPageQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_workspace_page import (
    TaskWorkspacePageQueryHandler,
)
from src.core.modules.project_management.gateway.task.reservation import (
    TaskReservationGateway,
)
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)


def build_project_management_tasks_desktop_api(
    *,
    project_service: ProjectService | None = None,
    task_service: TaskService | None = None,
    task_workspace_query: TaskWorkspacePageQueryHandler | None = None,
    task_detail_query: TaskDetailPageQueryHandler | None = None,
    task_dependency_diagnostics: TaskDependencyDiagnosticsQueryHandler | None = None,
    module_catalog_service: SupportsModuleEntitlements | None = None,
    project_resource_service: ProjectResourceService | None = None,
    resource_service: ResourceService | None = None,
    reservation_service: TaskReservationGateway | None = None,
    assignment_skill_validator: AssignmentSkillValidator | None = None,
    schedule_change_impact_service: ScheduleChangeImpactService | None = None,
) -> ProjectManagementTasksDesktopApi:
    return ProjectManagementTasksDesktopApi(
        project_service=project_service,
        task_service=task_service,
        task_workspace_query=task_workspace_query,
        task_detail_query=task_detail_query,
        task_dependency_diagnostics=task_dependency_diagnostics,
        module_catalog_service=module_catalog_service,
        project_resource_service=project_resource_service,
        resource_service=resource_service,
        reservation_service=reservation_service,
        assignment_skill_validator=assignment_skill_validator,
        schedule_change_impact_service=schedule_change_impact_service,
    )


__all__ = ["build_project_management_tasks_desktop_api"]
