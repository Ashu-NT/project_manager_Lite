from __future__ import annotations

from src.core.application.global_overview.contracts.action_center import ActionCenterContext
from src.core.application.global_overview.contracts.module_summary import ModuleSummaryDto
from src.core.modules.project_management.application.dashboard.services.dashboard_service import (
    DashboardService,
)
from src.core.modules.project_management.application.projects.service import ProjectService
from src.core.platform.application.platform_runtime.platform_runtime_service import (
    PlatformRuntimeApplicationService,
)
from src.core.platform.common.exceptions import BusinessRuleError

_MODULE_CODE = "project_management"


class ProjectManagementModuleOverviewContributor:
    """Project Management's Global Overview module card.

    Requires project_management to be enabled AND the current user to hold
    a project_management-relevant permission -- read through the single
    centralized `MODULE_PERMISSION_PREFIXES` policy via
    `list_accessible_modules()`, never a second copy of that rule. Returns
    None for either an unavailable or an inaccessible module; the
    orchestrator must not special-case this module by code.
    """

    def __init__(
        self,
        *,
        platform_runtime_application_service: PlatformRuntimeApplicationService,
        dashboard_service: DashboardService,
        project_service: ProjectService,
    ) -> None:
        self._platform_runtime_application_service = platform_runtime_application_service
        self._dashboard_service = dashboard_service
        self._project_service = project_service

    def get_summary(self, context: ActionCenterContext) -> ModuleSummaryDto | None:
        if not self._is_accessible():
            return None
        return ModuleSummaryDto(
            module_code=_MODULE_CODE,
            title="Project Management",
            description=(
                "Plan and monitor projects, tasks, resources, schedules, "
                "and delivery."
            ),
            summary_text=self._active_projects_summary_text(),
            route_id="project_management",
        )

    def _is_accessible(self) -> bool:
        accessible_codes = {
            module.code
            for module in self._platform_runtime_application_service.list_accessible_modules()
        }
        return _MODULE_CODE in accessible_codes

    def _active_projects_summary_text(self) -> str:
        # Reuses the existing portfolio dashboard's own active_projects
        # metric rather than recomputing the rule -- falls back to a plain
        # accessible-project count only if the user lacks report.view.
        try:
            data = self._dashboard_service.get_portfolio_data()
        except BusinessRuleError:
            project_count = len(self._project_service.list_projects())
            noun = "project" if project_count == 1 else "projects"
            return f"{project_count} {noun}"
        count = data.portfolio.active_projects
        noun = "active project" if count == 1 else "active projects"
        return f"{count} {noun}"


__all__ = ["ProjectManagementModuleOverviewContributor"]
