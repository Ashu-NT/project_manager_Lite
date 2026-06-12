"""Dashboard DTO models."""

from src.core.modules.project_management.api.desktop.dashboard.models.activity_feed import (
    ProjectDashboardActivityFeedDescriptor,
    ProjectDashboardActivityItemDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.charts import (
    ProjectDashboardChartDescriptor,
    ProjectDashboardChartPointDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.health_cards import (
    ProjectDashboardHealthCardDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.overview import (
    ProjectDashboardMetricDescriptor,
    ProjectDashboardOverviewDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.panels import (
    ProjectDashboardPanelDescriptor,
    ProjectDashboardPanelRowDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.sections import (
    ProjectDashboardSectionDescriptor,
    ProjectDashboardSectionItemDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.snapshot import (
    ProjectDashboardSelectorOptionDescriptor,
    ProjectDashboardSnapshotDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.tables import (
    ProjectDashboardOperationalTabDescriptor,
    ProjectDashboardOperationalTableDescriptor,
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
]
