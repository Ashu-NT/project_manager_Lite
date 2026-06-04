"""Dashboard desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.dashboard.api import (
    ProjectManagementDashboardDesktopApi,
)
from src.core.modules.project_management.api.desktop.dashboard.factories.dashboard_api_factory import (
    build_project_management_dashboard_desktop_api,
)
from src.core.modules.project_management.api.desktop.dashboard.models import (
    ProjectDashboardActivityFeedDescriptor,
    ProjectDashboardActivityItemDescriptor,
    ProjectDashboardChartDescriptor,
    ProjectDashboardChartPointDescriptor,
    ProjectDashboardHealthCardDescriptor,
    ProjectDashboardMetricDescriptor,
    ProjectDashboardOperationalTabDescriptor,
    ProjectDashboardOperationalTableDescriptor,
    ProjectDashboardOverviewDescriptor,
    ProjectDashboardPanelDescriptor,
    ProjectDashboardPanelRowDescriptor,
    ProjectDashboardSectionDescriptor,
    ProjectDashboardSectionItemDescriptor,
    ProjectDashboardSelectorOptionDescriptor,
    ProjectDashboardSnapshotDescriptor,
    ProjectDashboardTableColumnDescriptor,
    ProjectDashboardTableRowDescriptor,
)

__all__ = [
    "ProjectDashboardActivityFeedDescriptor",
    "ProjectDashboardActivityItemDescriptor",
    "ProjectDashboardChartDescriptor",
    "ProjectDashboardChartPointDescriptor",
    "ProjectDashboardHealthCardDescriptor",
    "ProjectDashboardMetricDescriptor",
    "ProjectDashboardOperationalTabDescriptor",
    "ProjectDashboardOperationalTableDescriptor",
    "ProjectDashboardOverviewDescriptor",
    "ProjectDashboardPanelDescriptor",
    "ProjectDashboardPanelRowDescriptor",
    "ProjectDashboardSectionDescriptor",
    "ProjectDashboardSectionItemDescriptor",
    "ProjectDashboardSelectorOptionDescriptor",
    "ProjectDashboardSnapshotDescriptor",
    "ProjectDashboardTableColumnDescriptor",
    "ProjectDashboardTableRowDescriptor",
    "ProjectManagementDashboardDesktopApi",
    "build_project_management_dashboard_desktop_api",
]
