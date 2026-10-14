from __future__ import annotations

from src.core.global_overview.contract.action_center import (
    ActionCenterContext,
)
from src.core.global_overview.contract.module_summary import (
    ModuleSummaryDto,
)
from src.core.modules.project_management.application.dashboard.reporting.portfolio import (
    PortfolioDashboardQueryHandler,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.platform.application.platform_runtime import (
    PlatformRuntimeQueryHandler,
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
        platform_runtime_query: PlatformRuntimeQueryHandler,
        portfolio_dashboard: PortfolioDashboardQueryHandler,
        project_service: ProjectQueryHandler,
    ) -> None:
        self._platform_runtime_query = platform_runtime_query
        self._portfolio_dashboard = portfolio_dashboard
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
            for module in self._platform_runtime_query.list_accessible_modules()
        }
        return _MODULE_CODE in accessible_codes

    def _active_projects_summary_text(self) -> str:
        # Reuses the existing portfolio dashboard's own active_projects
        # metric rather than recomputing the rule -- falls back to a plain
        # accessible-project count only if the user lacks report.view.
        try:
            data = self._portfolio_dashboard.get_portfolio_data()
        except BusinessRuleError:
            project_count = len(self._project_service.list_projects())
            noun = "project" if project_count == 1 else "projects"
            return f"{project_count} {noun}"
        if data.portfolio is None:
            return "Portfolio summary unavailable"
        count = data.portfolio.active_projects
        noun = "active project" if count == 1 else "active projects"
        return f"{count} {noun}"


__all__ = ["ProjectManagementModuleOverviewContributor"]
