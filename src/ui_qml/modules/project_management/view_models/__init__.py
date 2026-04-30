"""Project management QML view models."""
from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardMetricViewModel,
    ProjectDashboardOverviewViewModel,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogMetricViewModel,
    ProjectCatalogOverviewViewModel,
    ProjectCatalogWorkspaceViewModel,
    ProjectDetailFieldViewModel,
    ProjectDetailViewModel,
    ProjectRecordViewModel,
    ProjectStatusOptionViewModel,
)
from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogMetricViewModel,
    TaskCatalogOverviewViewModel,
    TaskCatalogWorkspaceViewModel,
    TaskDetailFieldViewModel,
    TaskDetailViewModel,
    TaskRecordViewModel,
    TaskSelectorOptionViewModel,
)
from src.ui_qml.modules.project_management.view_models.workspace import (
    ProjectManagementWorkspaceViewModel,
)

__all__ = [
    "ProjectCatalogMetricViewModel",
    "ProjectCatalogOverviewViewModel",
    "ProjectCatalogWorkspaceViewModel",
    "ProjectDashboardMetricViewModel",
    "ProjectDashboardOverviewViewModel",
    "ProjectDetailFieldViewModel",
    "ProjectDetailViewModel",
    "ProjectManagementWorkspaceViewModel",
    "ProjectRecordViewModel",
    "ProjectStatusOptionViewModel",
    "TaskCatalogMetricViewModel",
    "TaskCatalogOverviewViewModel",
    "TaskCatalogWorkspaceViewModel",
    "TaskDetailFieldViewModel",
    "TaskDetailViewModel",
    "TaskRecordViewModel",
    "TaskSelectorOptionViewModel",
]
