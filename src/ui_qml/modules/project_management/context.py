from __future__ import annotations

from PySide6.QtCore import Property, QObject, Slot

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


class ProjectManagementWorkspaceCatalog(QObject):
    def __init__(
        self,
        desktop_api_registry: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenters = build_project_management_workspace_presenters()
        dashboard_api = getattr(
            desktop_api_registry,
            "project_management_dashboard",
            None,
        )
        collaboration_api = getattr(
            desktop_api_registry,
            "project_management_collaboration",
            None,
        )
        projects_api = getattr(
            desktop_api_registry,
            "project_management_projects",
            None,
        )
        financials_api = getattr(
            desktop_api_registry,
            "project_management_financials",
            None,
        )
        portfolio_api = getattr(
            desktop_api_registry,
            "project_management_portfolio",
            None,
        )
        tasks_api = getattr(
            desktop_api_registry,
            "project_management_tasks",
            None,
        )
        resources_api = getattr(
            desktop_api_registry,
            "project_management_resources",
            None,
        )
        register_api = getattr(
            desktop_api_registry,
            "project_management_register",
            None,
        )
        risk_api = getattr(
            desktop_api_registry,
            "project_management_risk",
            register_api,
        )
        scheduling_api = getattr(
            desktop_api_registry,
            "project_management_scheduling",
            None,
        )
        timesheets_api = getattr(
            desktop_api_registry,
            "project_management_timesheets",
            None,
        )
        self._projects_workspace = ProjectManagementProjectsWorkspaceController(
            projects_workspace_presenter=ProjectProjectsWorkspacePresenter(
                desktop_api=projects_api
            ),
            parent=self,
        )
        self._financials_workspace = (
            ProjectManagementFinancialsWorkspaceController(
                financials_workspace_presenter=ProjectFinancialsWorkspacePresenter(
                    desktop_api=financials_api
                ),
                parent=self,
            )
        )
        self._portfolio_workspace = (
            ProjectManagementPortfolioWorkspaceController(
                portfolio_workspace_presenter=ProjectPortfolioWorkspacePresenter(
                    desktop_api=portfolio_api
                ),
                parent=self,
            )
        )
        self._resources_workspace = ProjectManagementResourcesWorkspaceController(
            resources_workspace_presenter=ProjectResourcesWorkspacePresenter(
                desktop_api=resources_api
            ),
            parent=self,
        )
        self._risk_workspace = ProjectManagementRegisterWorkspaceController(
            workspace_presenter=ProjectManagementWorkspacePresenter(
                "project_management.risk"
            ),
            register_workspace_presenter=ProjectRegisterWorkspacePresenter(
                desktop_api=risk_api,
                workspace_mode="risk",
            ),
            parent=self,
        )
        self._register_workspace = ProjectManagementRegisterWorkspaceController(
            workspace_presenter=ProjectManagementWorkspacePresenter(
                "project_management.register"
            ),
            register_workspace_presenter=ProjectRegisterWorkspacePresenter(
                desktop_api=register_api,
                workspace_mode="register",
            ),
            parent=self,
        )
        self._scheduling_workspace = ProjectManagementSchedulingWorkspaceController(
            scheduling_workspace_presenter=ProjectSchedulingWorkspacePresenter(
                desktop_api=scheduling_api
            ),
            parent=self,
        )
        self._tasks_workspace = ProjectManagementTasksWorkspaceController(
            tasks_workspace_presenter=ProjectTasksWorkspacePresenter(
                desktop_api=tasks_api
            ),
            parent=self,
        )
        self._dashboard_workspace = ProjectManagementDashboardWorkspaceController(
            dashboard_workspace_presenter=ProjectDashboardWorkspacePresenter(
                desktop_api=dashboard_api
            ),
            parent=self
        )
        self._collaboration_workspace = (
            ProjectManagementCollaborationWorkspaceController(
                collaboration_workspace_presenter=ProjectCollaborationWorkspacePresenter(
                    desktop_api=collaboration_api
                ),
                parent=self,
            )
        )
        self._timesheets_workspace = (
            ProjectManagementTimesheetsWorkspaceController(
                timesheets_workspace_presenter=ProjectTimesheetsWorkspacePresenter(
                    desktop_api=timesheets_api
                ),
                parent=self,
            )
        )

    @Property(ProjectManagementProjectsWorkspaceController, constant=True)
    def projectsWorkspace(self) -> ProjectManagementProjectsWorkspaceController:
        return self._projects_workspace

    @Property(ProjectManagementResourcesWorkspaceController, constant=True)
    def resourcesWorkspace(self) -> ProjectManagementResourcesWorkspaceController:
        return self._resources_workspace

    @Property(ProjectManagementRegisterWorkspaceController, constant=True)
    def riskWorkspace(self) -> ProjectManagementRegisterWorkspaceController:
        return self._risk_workspace

    @Property(ProjectManagementRegisterWorkspaceController, constant=True)
    def registerWorkspace(self) -> ProjectManagementRegisterWorkspaceController:
        return self._register_workspace

    @Property(ProjectManagementFinancialsWorkspaceController, constant=True)
    def financialsWorkspace(self) -> ProjectManagementFinancialsWorkspaceController:
        return self._financials_workspace

    @Property(ProjectManagementPortfolioWorkspaceController, constant=True)
    def portfolioWorkspace(self) -> ProjectManagementPortfolioWorkspaceController:
        return self._portfolio_workspace

    @Property(ProjectManagementSchedulingWorkspaceController, constant=True)
    def schedulingWorkspace(self) -> ProjectManagementSchedulingWorkspaceController:
        return self._scheduling_workspace

    @Property(ProjectManagementTasksWorkspaceController, constant=True)
    def tasksWorkspace(self) -> ProjectManagementTasksWorkspaceController:
        return self._tasks_workspace

    @Property(ProjectManagementDashboardWorkspaceController, constant=True)
    def dashboardWorkspace(self) -> ProjectManagementDashboardWorkspaceController:
        return self._dashboard_workspace

    @Property(ProjectManagementCollaborationWorkspaceController, constant=True)
    def collaborationWorkspace(self) -> ProjectManagementCollaborationWorkspaceController:
        return self._collaboration_workspace

    @Property(ProjectManagementTimesheetsWorkspaceController, constant=True)
    def timesheetsWorkspace(self) -> ProjectManagementTimesheetsWorkspaceController:
        return self._timesheets_workspace

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
        return dict(self._dashboard_workspace.overview)


__all__ = ["ProjectManagementWorkspaceCatalog"]
