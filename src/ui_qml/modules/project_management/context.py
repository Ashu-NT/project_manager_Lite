from __future__ import annotations

from PySide6.QtCore import Property, QObject, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.api.desktop.integration import IntegrationCapabilityDesktopApi

from src.ui_qml.modules.project_management.controllers import (
    ProjectManagementCollaborationWorkspaceController,
    ProjectManagementDashboardWorkspaceController,
    ProjectManagementFinancialsWorkspaceController,
    ProjectManagementPortfolioWorkspaceController,
    ProjectManagementProjectsWorkspaceController,
    ProjectManagementRegisterWorkspaceController,
    ProjectManagementResourcesWorkspaceController,
    ProjectManagementSchedulingWorkspaceController,
    ProjectManagementTasksWorkspaceController,
    ProjectManagementTimesheetsWorkspaceController,
)
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementTaskViewStore,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectCollaborationWorkspacePresenter,
    ProjectDashboardWorkspacePresenter,
    ProjectFinancialsWorkspacePresenter,
    ProjectManagementWorkspacePresenter,
    ProjectPortfolioWorkspacePresenter,
    ProjectProjectsWorkspacePresenter,
    ProjectRegisterWorkspacePresenter,
    ProjectResourcesWorkspacePresenter,
    ProjectSchedulingWorkspacePresenter,
    ProjectTasksWorkspacePresenter,
    ProjectTimesheetsWorkspacePresenter,
    build_project_management_workspace_presenters,
)

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace catalogs are provided by the shell runtime.")
class ProjectManagementWorkspaceCatalog(QObject):
    def __init__(
        self,
        desktop_api_registry: object | None = None,
        task_view_store: ProjectManagementTaskViewStore | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenters = build_project_management_workspace_presenters()
        self._task_view_store = task_view_store or ProjectManagementTaskViewStore()
        self._dashboard_api = getattr(
            desktop_api_registry,
            "project_management_dashboard",
            None,
        )
        self._collaboration_api = getattr(
            desktop_api_registry,
            "project_management_collaboration",
            None,
        )
        self._approval_api = getattr(
            desktop_api_registry,
            "platform_approval",
            None,
        )
        self._projects_api = getattr(
            desktop_api_registry,
            "project_management_projects",
            None,
        )
        self._financials_api = getattr(
            desktop_api_registry,
            "project_management_financials",
            None,
        )
        self._portfolio_api = getattr(
            desktop_api_registry,
            "project_management_portfolio",
            None,
        )
        self._tasks_api = getattr(
            desktop_api_registry,
            "project_management_tasks",
            None,
        )
        self._resources_api = getattr(
            desktop_api_registry,
            "project_management_resources",
            None,
        )
        self._register_api = getattr(
            desktop_api_registry,
            "project_management_register",
            None,
        )
        self._risk_api = getattr(
            desktop_api_registry,
            "project_management_risk",
            self._register_api,
        )
        self._scheduling_api = getattr(
            desktop_api_registry,
            "project_management_scheduling",
            None,
        )
        self._timesheets_api = getattr(
            desktop_api_registry,
            "project_management_timesheets",
            None,
        )
        self._integration_api: IntegrationCapabilityDesktopApi | None = (
            getattr(desktop_api_registry, "integration_capability", None)
            if desktop_api_registry is not None else None
        )
        self._projects_workspace: ProjectManagementProjectsWorkspaceController | None = None
        self._financials_workspace: ProjectManagementFinancialsWorkspaceController | None = None
        self._portfolio_workspace: ProjectManagementPortfolioWorkspaceController | None = None
        self._resources_workspace: ProjectManagementResourcesWorkspaceController | None = None
        self._risk_workspace: ProjectManagementRegisterWorkspaceController | None = None
        self._register_workspace: ProjectManagementRegisterWorkspaceController | None = None
        self._scheduling_workspace: ProjectManagementSchedulingWorkspaceController | None = None
        self._tasks_workspace: ProjectManagementTasksWorkspaceController | None = None
        self._dashboard_workspace: ProjectManagementDashboardWorkspaceController | None = None
        self._collaboration_workspace: ProjectManagementCollaborationWorkspaceController | None = None
        self._timesheets_workspace: ProjectManagementTimesheetsWorkspaceController | None = None

    def _get_projects_workspace(self) -> ProjectManagementProjectsWorkspaceController:
        if self._projects_workspace is None:
            self._projects_workspace = ProjectManagementProjectsWorkspaceController(
                projects_workspace_presenter=ProjectProjectsWorkspacePresenter(
                    desktop_api=self._projects_api,
                    tasks_desktop_api=self._tasks_api,
                ),
                parent=self,
            )
        return self._projects_workspace

    def _get_resources_workspace(self) -> ProjectManagementResourcesWorkspaceController:
        if self._resources_workspace is None:
            self._resources_workspace = ProjectManagementResourcesWorkspaceController(
                resources_workspace_presenter=ProjectResourcesWorkspacePresenter(
                    desktop_api=self._resources_api
                ),
                parent=self,
            )
        return self._resources_workspace

    def _get_risk_workspace(self) -> ProjectManagementRegisterWorkspaceController:
        if self._risk_workspace is None:
            self._risk_workspace = ProjectManagementRegisterWorkspaceController(
                workspace_presenter=ProjectManagementWorkspacePresenter(
                    "project_management.risk"
                ),
                register_workspace_presenter=ProjectRegisterWorkspacePresenter(
                    desktop_api=self._risk_api,
                    workspace_mode="risk",
                ),
                parent=self,
            )
        return self._risk_workspace

    def _get_register_workspace(self) -> ProjectManagementRegisterWorkspaceController:
        if self._register_workspace is None:
            self._register_workspace = ProjectManagementRegisterWorkspaceController(
                workspace_presenter=ProjectManagementWorkspacePresenter(
                    "project_management.register"
                ),
                register_workspace_presenter=ProjectRegisterWorkspacePresenter(
                    desktop_api=self._register_api,
                    workspace_mode="register",
                ),
                parent=self,
            )
        return self._register_workspace

    def _get_financials_workspace(self) -> ProjectManagementFinancialsWorkspaceController:
        if self._financials_workspace is None:
            self._financials_workspace = ProjectManagementFinancialsWorkspaceController(
                financials_workspace_presenter=ProjectFinancialsWorkspacePresenter(
                    desktop_api=self._financials_api
                ),
                parent=self,
            )
        return self._financials_workspace

    def _get_portfolio_workspace(self) -> ProjectManagementPortfolioWorkspaceController:
        if self._portfolio_workspace is None:
            self._portfolio_workspace = ProjectManagementPortfolioWorkspaceController(
                portfolio_workspace_presenter=ProjectPortfolioWorkspacePresenter(
                    desktop_api=self._portfolio_api
                ),
                parent=self,
            )
        return self._portfolio_workspace

    def _get_scheduling_workspace(self) -> ProjectManagementSchedulingWorkspaceController:
        if self._scheduling_workspace is None:
            self._scheduling_workspace = ProjectManagementSchedulingWorkspaceController(
                scheduling_workspace_presenter=ProjectSchedulingWorkspacePresenter(
                    desktop_api=self._scheduling_api
                ),
                parent=self,
            )
        return self._scheduling_workspace

    def _get_tasks_workspace(self) -> ProjectManagementTasksWorkspaceController:
        if self._tasks_workspace is None:
            self._tasks_workspace = ProjectManagementTasksWorkspaceController(
                tasks_workspace_presenter=ProjectTasksWorkspacePresenter(
                    desktop_api=self._tasks_api,
                    collaboration_desktop_api=self._collaboration_api,
                    timesheets_desktop_api=self._timesheets_api,
                ),
                task_view_store=self._task_view_store,
                parent=self,
            )
        return self._tasks_workspace

    def _get_dashboard_workspace(self) -> ProjectManagementDashboardWorkspaceController:
        if self._dashboard_workspace is None:
            self._dashboard_workspace = ProjectManagementDashboardWorkspaceController(
                dashboard_workspace_presenter=ProjectDashboardWorkspacePresenter(
                    desktop_api=self._dashboard_api
                ),
                parent=self,
            )
        return self._dashboard_workspace

    def _get_collaboration_workspace(self) -> ProjectManagementCollaborationWorkspaceController:
        if self._collaboration_workspace is None:
            self._collaboration_workspace = ProjectManagementCollaborationWorkspaceController(
                collaboration_workspace_presenter=ProjectCollaborationWorkspacePresenter(
                    desktop_api=self._collaboration_api,
                    approval_api=self._approval_api,
                ),
                parent=self,
            )
        return self._collaboration_workspace

    def _get_timesheets_workspace(self) -> ProjectManagementTimesheetsWorkspaceController:
        if self._timesheets_workspace is None:
            self._timesheets_workspace = ProjectManagementTimesheetsWorkspaceController(
                timesheets_workspace_presenter=ProjectTimesheetsWorkspacePresenter(
                    desktop_api=self._timesheets_api
                ),
                parent=self,
            )
        return self._timesheets_workspace

    @Property(ProjectManagementProjectsWorkspaceController, constant=True)
    def projectsWorkspace(self) -> ProjectManagementProjectsWorkspaceController:
        return self._get_projects_workspace()

    @Property(ProjectManagementResourcesWorkspaceController, constant=True)
    def resourcesWorkspace(self) -> ProjectManagementResourcesWorkspaceController:
        return self._get_resources_workspace()

    @Property(ProjectManagementRegisterWorkspaceController, constant=True)
    def riskWorkspace(self) -> ProjectManagementRegisterWorkspaceController:
        return self._get_risk_workspace()

    @Property(ProjectManagementRegisterWorkspaceController, constant=True)
    def registerWorkspace(self) -> ProjectManagementRegisterWorkspaceController:
        return self._get_register_workspace()

    @Property(ProjectManagementFinancialsWorkspaceController, constant=True)
    def financialsWorkspace(self) -> ProjectManagementFinancialsWorkspaceController:
        return self._get_financials_workspace()

    @Property(ProjectManagementPortfolioWorkspaceController, constant=True)
    def portfolioWorkspace(self) -> ProjectManagementPortfolioWorkspaceController:
        return self._get_portfolio_workspace()

    @Property(ProjectManagementSchedulingWorkspaceController, constant=True)
    def schedulingWorkspace(self) -> ProjectManagementSchedulingWorkspaceController:
        return self._get_scheduling_workspace()

    @Property(ProjectManagementTasksWorkspaceController, constant=True)
    def tasksWorkspace(self) -> ProjectManagementTasksWorkspaceController:
        return self._get_tasks_workspace()

    @Property(ProjectManagementDashboardWorkspaceController, constant=True)
    def dashboardWorkspace(self) -> ProjectManagementDashboardWorkspaceController:
        return self._get_dashboard_workspace()

    @Property(ProjectManagementCollaborationWorkspaceController, constant=True)
    def collaborationWorkspace(self) -> ProjectManagementCollaborationWorkspaceController:
        return self._get_collaboration_workspace()

    @Property(ProjectManagementTimesheetsWorkspaceController, constant=True)
    def timesheetsWorkspace(self) -> ProjectManagementTimesheetsWorkspaceController:
        return self._get_timesheets_workspace()

    @Slot(str, result="QVariantMap")
    def workspace(self, route_id: str) -> dict[str, str]:
        presenter = self._presenters.get(route_id)
        if presenter is None:
            return {
                "routeId": route_id,
                "title": "",
                "summary": "",
                "migrationStatus": "",
                "legacyRuntimeStatus": "",
            }
        return serialize_workspace_view_model(presenter.build_view_model())

    @Slot(result="QVariantMap")
    def dashboardOverview(self) -> dict[str, object]:
        return dict(self._get_dashboard_workspace().overview)

    @Slot(str, result=bool)
    def isModuleEnabled(self, module_code: str) -> bool:
        if self._integration_api is None:
            return False
        return self._integration_api.is_module_enabled(module_code)

    @Slot(str, result=bool)
    def hasCapability(self, capability_id: str) -> bool:
        if self._integration_api is None:
            return False
        return self._integration_api.has_capability(capability_id)

    @Slot(str, str, str, result=bool)
    def canUseIntegration(self, source_module: str, target_module: str, capability: str) -> bool:
        if self._integration_api is None:
            return False
        return self._integration_api.can_use_integration(source_module, target_module, capability)

    @Slot(result="QVariantMap")
    def capabilitySnapshot(self) -> dict[str, bool]:
        if self._integration_api is None:
            return {}
        return self._integration_api.capability_snapshot()


__all__ = ["ProjectManagementWorkspaceCatalog"]
