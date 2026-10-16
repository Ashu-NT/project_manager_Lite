"""Thin access to dashboard application queries; QML formatting belongs to presenters."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from src.core.modules.project_management.application.collaboration.queries.collaboration_inbox import (
    CollaborationInboxQueryHandler,
)
from src.core.modules.project_management.application.dashboard import (
    DashboardData,
    PortfolioDashboardQueryHandler,
    ProjectDashboardQueryHandler,
)
from src.core.modules.project_management.application.financials.earned_value.dto.responses.earned_value import (
    EvmSeriesPoint,
)
from src.core.modules.project_management.application.projects.dto.responses.project import (
    ProjectResponse,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.application.reporting.builders.evm import (
    EarnedValueReportBuilder,
)
from src.core.modules.project_management.application.scheduling.baselines.queries.catalog import (
    BaselineQueryHandler,
)
from src.core.modules.project_management.application.scheduling.dto.responses.baselines import (
    SchedulingBaselineVarianceRowDto,
)
from src.core.modules.project_management.application.tasks.queries.task_workspace_page import (
    TaskWorkspacePageQueryHandler,
)
from src.core.modules.project_management.contracts.reads.tasks.models import (
    TaskWorkspaceReadPage,
)
from src.core.modules.project_management.domain.collaboration import (
    CollaborationInboxItem,
)
from src.core.modules.project_management.domain.scheduling.baseline import (
    ProjectBaseline,
)
from src.core.platform.application.approval.dto.responses.requests import (
    ApprovalRequestResponse,
)
from src.core.platform.application.approval.queries import ApprovalQueryHandler
from src.core.platform.application.tenant.modules.authorization import (
    require_module_enabled,
)
from src.core.platform.common.exceptions import ConfigurationError
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)


class ProjectManagementDashboardDesktopApi:
    def __init__(
        self, *, project_service: ProjectQueryHandler | None = None, project_dashboard: ProjectDashboardQueryHandler | None = None, portfolio_dashboard: PortfolioDashboardQueryHandler | None = None,
        baseline_query: BaselineQueryHandler | None = None, earned_value_report: EarnedValueReportBuilder | None = None, collaboration_inbox_query: CollaborationInboxQueryHandler | None = None,
        approval_queries: ApprovalQueryHandler | None = None, task_workspace_query: TaskWorkspacePageQueryHandler | None = None, module_catalog_service: SupportsModuleEntitlements | None = None,
    ) -> None:
        self._project_service = project_service
        self._project_dashboard = project_dashboard
        self._portfolio_dashboard = portfolio_dashboard
        self._baseline_query = baseline_query
        self._earned_value_report = earned_value_report
        self._collaboration_inbox_query = collaboration_inbox_query
        self._approval_queries = approval_queries
        self._task_workspace_query = task_workspace_query
        self._module_catalog_service = module_catalog_service

    @property
    def is_connected(self) -> bool:
        return self._project_dashboard is not None and self._portfolio_dashboard is not None

    @property
    def has_activity_feed(self) -> bool:
        return self._collaboration_inbox_query is not None

    def list_projects(self) -> Sequence[ProjectResponse]:
        return () if self._project_service is None else self._project_service.list_projects()

    def list_baselines(self, project_id: str) -> Sequence[ProjectBaseline]:
        return () if self._baseline_query is None else self._baseline_query.list_baselines(project_id)

    def get_dashboard_data(self, project_id: str, *, baseline_id: str | None = None, include_evm: bool = True) -> DashboardData:
        if self._project_dashboard is None:
            raise ConfigurationError("Project dashboard query is not connected.")
        return self._project_dashboard.get_dashboard_data(project_id, baseline_id=baseline_id, include_evm=include_evm)

    def get_portfolio_data(self) -> DashboardData:
        if self._portfolio_dashboard is None:
            raise ConfigurationError("Portfolio dashboard query is not connected.")
        return self._portfolio_dashboard.get_portfolio_data()

    def get_approved_baseline(self, project_id: str) -> ProjectBaseline | None:
        return None if self._baseline_query is None else self._baseline_query.get_approved_baseline(project_id)

    def list_variance_records(self, baseline_id: str) -> Sequence[SchedulingBaselineVarianceRowDto]:
        return () if self._baseline_query is None else self._baseline_query.query_variance_responses(baseline_id)

    def get_evm_series(self, project_id: str, *, baseline_id: str | None = None, as_of: date | None = None) -> Sequence[EvmSeriesPoint]:
        return () if self._earned_value_report is None else self._earned_value_report.get_evm_series(project_id, baseline_id=baseline_id, as_of=as_of)

    def list_recent_activity(self, *, project_id: str | None = None, created_since: datetime | None = None, limit: int = 120) -> Sequence[CollaborationInboxItem]:
        return () if self._collaboration_inbox_query is None else self._collaboration_inbox_query.list_recent_activity(project_id=project_id, created_since=created_since, limit=limit)

    def list_pending(self, *, project_id: str | None = None, limit: int = 120) -> Sequence[ApprovalRequestResponse]:
        return () if self._approval_queries is None else self._approval_queries.list_requests(status="PENDING", project_id=project_id, limit=limit)

    def list_delayed_tasks_page(
        self,
        *,
        project_id: str | None = None,
        search_text: str = "",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "endDateLabel",
        sort_direction: str = "asc",
    ) -> TaskWorkspaceReadPage | None:
        """Overview's "Delays" tab: SCALABLE (overdue tasks scale with task
        volume, not inherently bounded) -- authoritatively server-paginated
        by reusing Tasks' own workspace query handler (schedule="overdue")
        rather than a duplicate PM-Dashboard-owned reader. project_id=None
        means "all accessible projects" (portfolio scope), matching
        TaskWorkspaceReader's own falsy-check semantics.
        """
        require_module_enabled(
            self._module_catalog_service,
            "project_management",
            operation_label="query workspace page",
        )
        if self._task_workspace_query is None:
            return None
        return self._task_workspace_query.query_workspace_page(
            project_id=project_id, search_text=search_text, status="all", priority="all",
            schedule="overdue", page=page, page_size=page_size,
            sort_key=sort_key, sort_direction=sort_direction,
        )


__all__ = ["ProjectManagementDashboardDesktopApi"]
