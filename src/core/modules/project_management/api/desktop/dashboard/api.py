"""ProjectManagementDashboardDesktopApi — thin desktop dashboard facade."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.dashboard.models.overview import (
    ProjectDashboardOverviewDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.snapshot import (
    ProjectDashboardSnapshotDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.overview_builder import (
    build_empty_overview,
    build_overview_from_dashboard_data,
)
from src.core.modules.project_management.api.desktop.dashboard.services.dashboard_snapshot_service import (
    DashboardSnapshotService,
)


class ProjectManagementDashboardDesktopApi:
    """Thin facade — all orchestration delegates to DashboardSnapshotService."""

    def __init__(
        self,
        *,
        project_service=None,
        dashboard_service=None,
        baseline_service=None,
        reporting_service=None,
        register_service=None,
        collaboration_service=None,
        approval_service=None,
    ) -> None:
        self._snapshot_service = DashboardSnapshotService(
            project_service=project_service,
            dashboard_service=dashboard_service,
            baseline_service=baseline_service,
            reporting_service=reporting_service,
            register_service=register_service,
            collaboration_service=collaboration_service,
            approval_service=approval_service,
        )

    def build_empty_overview(self) -> ProjectDashboardOverviewDescriptor:
        return build_empty_overview()

    def build_overview_from_dashboard_data(
        self, *, project_name: str, dashboard_data
    ) -> ProjectDashboardOverviewDescriptor:
        return build_overview_from_dashboard_data(
            project_name=project_name, dashboard_data=dashboard_data
        )

    def build_snapshot(
        self,
        *,
        project_id: str | None = None,
        baseline_id: str | None = None,
        period_key: str | None = None,
        view_key: str | None = None,
    ) -> ProjectDashboardSnapshotDescriptor:
        return self._snapshot_service.build_snapshot(
            project_id=project_id,
            baseline_id=baseline_id,
            period_key=period_key,
            view_key=view_key,
        )


__all__ = ["ProjectManagementDashboardDesktopApi"]
