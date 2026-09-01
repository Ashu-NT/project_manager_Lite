from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.core.platform.api.desktop.integration import IntegrationCapabilityDesktopApi

from src.ui_qml.platform.adapters.approval_view_invalidation_adapter import (
    ApprovalViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.employee_view_invalidation_adapter import (
    EmployeeViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.financial_profile_view_invalidation_adapter import (
    FinancialProfileViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.forecast_view_invalidation_adapter import (
    ForecastViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.resource_view_invalidation_adapter import (
    ResourceViewInvalidationAdapter,
)
from src.ui_qml.platform.presenters.tenants.tenant_switcher_presenter import (
    TenantSwitcherPresenter,
)
from src.ui_qml.modules.project_management.controllers import (
    ProjectManagementCollaborationWorkspaceController,
    ProjectManagementDashboardWorkspaceController,
    ProjectManagementFinancialsWorkspaceController,
    ProjectManagementPortfolioWorkspaceController,
    ProjectManagementResourceTimesheetsController,
    ProjectManagementProjectsWorkspaceController,
    ProjectManagementRegisterWorkspaceController,
    ProjectManagementResourcesWorkspaceController,
    ProjectManagementSchedulingWorkspaceController,
    ProjectManagementTasksWorkspaceController,
    ProjectManagementTimesheetsWorkspaceController,
)
from src.ui_qml.modules.project_management.controllers.common import (
    PMWorkspaceNavigationController,
    resolve_active_organization_id_from_runtime_api,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.controllers.common.pm_capability_controller import (
    PMCapabilityController,
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
from src.ui_qml.modules.project_management.presenters.resource_timesheets import (
    ResourceTimesheetsPresenter,
)

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace catalogs are provided by the shell runtime.")
class ProjectManagementWorkspaceCatalog(QObject):
    def __init__(
        self,
        desktop_api_registry: object | None = None,
        auth_engine: Any | None = None,
        user_session_provider: Callable[[], Any | None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenters = build_project_management_workspace_presenters()
        self._desktop_api_registry = desktop_api_registry
        self._platform_runtime_api = (
            getattr(desktop_api_registry, "platform_runtime", None)
            if desktop_api_registry is not None else None
        )
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

        self._view_invalidation_channel = (
            getattr(desktop_api_registry, "platform_view_invalidation_channel", None)
            if desktop_api_registry is not None else None
        )

        self._tenant_switcher_presenter = TenantSwitcherPresenter(
            tenant_api=(
                getattr(desktop_api_registry, "platform_tenant", None)
                if desktop_api_registry is not None else None
            )
        )
        self._approval_view_invalidation_adapter: ApprovalViewInvalidationAdapter | None = None
        self._employee_view_invalidation_adapter: EmployeeViewInvalidationAdapter | None = None
        self._forecast_view_invalidation_adapter: ForecastViewInvalidationAdapter | None = None
        self._financial_profile_view_invalidation_adapter: FinancialProfileViewInvalidationAdapter | None = None
        self._resource_view_invalidation_adapter: ResourceViewInvalidationAdapter | None = None
        self._portfolio_resource_view_invalidation_adapter: ResourceViewInvalidationAdapter | None = None
        self._scheduling_resource_view_invalidation_adapter: ResourceViewInvalidationAdapter | None = None
        self._tasks_resource_view_invalidation_adapter: ResourceViewInvalidationAdapter | None = None
        self._dashboard_resource_view_invalidation_adapter: ResourceViewInvalidationAdapter | None = None
        self._timesheets_resource_view_invalidation_adapter: ResourceViewInvalidationAdapter | None = None
        self._review_queue_resource_view_invalidation_adapter: ResourceViewInvalidationAdapter | None = None
        self._pm_capability = PMCapabilityController(
            auth_engine=auth_engine,
            user_session_provider=user_session_provider,
            parent=self,
        )
        # R2.3: the PM-wide canonical-navigation state owner. Constructed
        # eagerly (like PMCapabilityController above) since it is cheap
        # cross-cutting state, not a heavy per-capability workspace.
        self._pm_navigation = PMWorkspaceNavigationController(parent=self)
        self._projects_workspace: ProjectManagementProjectsWorkspaceController | None = None
        self._financials_workspace: ProjectManagementFinancialsWorkspaceController | None = None
        self._portfolio_workspace: ProjectManagementPortfolioWorkspaceController | None = None
        self._resources_workspace: ProjectManagementResourcesWorkspaceController | None = None
        self._register_workspace: ProjectManagementRegisterWorkspaceController | None = None
        self._scheduling_workspace: ProjectManagementSchedulingWorkspaceController | None = None
        self._tasks_workspace: ProjectManagementTasksWorkspaceController | None = None
        self._dashboard_workspace: ProjectManagementDashboardWorkspaceController | None = None
        self._collaboration_workspace: ProjectManagementCollaborationWorkspaceController | None = None
        self._timesheets_workspace: ProjectManagementResourceTimesheetsController | None = None
        self._review_queue_workspace: ProjectManagementTimesheetsWorkspaceController | None = None

    def _active_tenant_id(self) -> str | None:
        try:
            return self._tenant_switcher_presenter.get_active_tenant_id() or None
        except Exception:
            return None

    def _active_organization_id(self) -> str | None:
        runtime_api = self._platform_runtime_api
        if runtime_api is None:
            return None
        try:
            return resolve_active_organization_id_from_runtime_api(runtime_api)
        except Exception:
            return None

    def _get_projects_workspace(self) -> ProjectManagementProjectsWorkspaceController:
        if self._projects_workspace is None:
            self._projects_workspace = ProjectManagementProjectsWorkspaceController(
                projects_workspace_presenter=ProjectProjectsWorkspacePresenter(
                    desktop_api=self._projects_api,
                    tasks_desktop_api=self._tasks_api,
                    site_api=getattr(self._desktop_api_registry, "platform_site", None),
                    department_api=getattr(self._desktop_api_registry, "platform_department", None),
                    user_api=getattr(self._desktop_api_registry, "platform_user", None),
                    employee_api=getattr(self._desktop_api_registry, "platform_employee", None),
                    activity_api=getattr(self._desktop_api_registry, "platform_activity", None),
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

            self._employee_view_invalidation_adapter = EmployeeViewInvalidationAdapter(
                channel=self._view_invalidation_channel,
                tenant_id=self._active_tenant_id() or "",
                organization_id=self._active_organization_id() or "",
                parent=self,
            )
            self._employee_view_invalidation_adapter.employeeCollectionStale.connect(
                self._resources_workspace.refresh_employee_options
            )

            self._resource_view_invalidation_adapter = ResourceViewInvalidationAdapter(
                channel=self._view_invalidation_channel,
                tenant_id=self._active_tenant_id() or "",
                organization_id=self._active_organization_id() or "",
                parent=self,
            )
            self._resource_view_invalidation_adapter.resourceListStale.connect(
                self._resources_workspace.onResourceListStale
            )
            self._resource_view_invalidation_adapter.resourceCapabilitiesStale.connect(
                self._resources_workspace.onResourceCapabilitiesStale
            )
        return self._resources_workspace

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
                    desktop_api=self._financials_api,
                    approval_api=self._approval_api,
                    audit_api=getattr(
                        self._desktop_api_registry,
                        "platform_enterprise_audit",
                        None,
                    ),
                ),
                parent=self,
            )

            self._forecast_view_invalidation_adapter = ForecastViewInvalidationAdapter(
                channel=self._view_invalidation_channel,
                tenant_id=self._active_tenant_id() or "",
                organization_id=self._active_organization_id() or "",
                parent=self,
            )
            self._forecast_view_invalidation_adapter.forecastPlanningStale.connect(
                self._financials_workspace.onForecastPlanningStale
            )
            self._forecast_view_invalidation_adapter.forecastApprovedBasisStale.connect(
                self._financials_workspace.onForecastApprovedBasisStale
            )

            self._financial_profile_view_invalidation_adapter = FinancialProfileViewInvalidationAdapter(
                channel=self._view_invalidation_channel,
                tenant_id=self._active_tenant_id() or "",
                organization_id=self._active_organization_id() or "",
                parent=self,
            )
            self._financial_profile_view_invalidation_adapter.financialProfileStale.connect(
                self._financials_workspace.onFinancialProfileStale
            )
        return self._financials_workspace

    def _wire_resource_list_stale(self, controller) -> ResourceViewInvalidationAdapter:
        adapter = ResourceViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        adapter.resourceListStale.connect(lambda _resource_id: controller._request_domain_refresh())
        return adapter

    def _get_portfolio_workspace(self) -> ProjectManagementPortfolioWorkspaceController:
        if self._portfolio_workspace is None:
            self._portfolio_workspace = ProjectManagementPortfolioWorkspaceController(
                portfolio_workspace_presenter=ProjectPortfolioWorkspacePresenter(
                    desktop_api=self._portfolio_api
                ),
                parent=self,
            )
            self._portfolio_resource_view_invalidation_adapter = self._wire_resource_list_stale(
                self._portfolio_workspace
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
            self._scheduling_resource_view_invalidation_adapter = self._wire_resource_list_stale(
                self._scheduling_workspace
            )
        return self._scheduling_workspace

    def _get_tasks_workspace(self) -> ProjectManagementTasksWorkspaceController:
        if self._tasks_workspace is None:
            self._tasks_workspace = ProjectManagementTasksWorkspaceController(
                tasks_workspace_presenter=ProjectTasksWorkspacePresenter(
                    desktop_api=self._tasks_api,
                    collaboration_desktop_api=self._collaboration_api,
                    timesheets_desktop_api=self._timesheets_api,
                    user_api=getattr(self._desktop_api_registry, "platform_user", None),
                    employee_api=getattr(self._desktop_api_registry, "platform_employee", None),
                    activity_api=getattr(self._desktop_api_registry, "platform_activity", None),
                    projects_desktop_api=self._projects_api,
                ),
                parent=self,
            )
            self._tasks_resource_view_invalidation_adapter = self._wire_resource_list_stale(
                self._tasks_workspace
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
            self._dashboard_resource_view_invalidation_adapter = self._wire_resource_list_stale(
                self._dashboard_workspace
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

            self._approval_view_invalidation_adapter = ApprovalViewInvalidationAdapter(
                channel=self._view_invalidation_channel,
                tenant_id=self._active_tenant_id() or "",
                organization_id=self._active_organization_id() or "",
                parent=self,
            )
            self._approval_view_invalidation_adapter.approvalsStale.connect(
                self._collaboration_workspace.refresh_approvals
            )
        return self._collaboration_workspace

    def _get_timesheets_workspace(self) -> ProjectManagementResourceTimesheetsController:
        if self._timesheets_workspace is None:
            self._timesheets_workspace = ProjectManagementResourceTimesheetsController(
                presenter=ResourceTimesheetsPresenter(desktop_api=self._timesheets_api),
                parent=self,
            )
            self._timesheets_resource_view_invalidation_adapter = self._wire_resource_list_stale(
                self._timesheets_workspace
            )
        return self._timesheets_workspace

    def _get_review_queue_workspace(self) -> ProjectManagementTimesheetsWorkspaceController:
        if self._review_queue_workspace is None:
            self._review_queue_workspace = ProjectManagementTimesheetsWorkspaceController(
                timesheets_workspace_presenter=ProjectTimesheetsWorkspacePresenter(
                    desktop_api=self._timesheets_api
                ),
                parent=self,
            )
            self._review_queue_resource_view_invalidation_adapter = self._wire_resource_list_stale(
                self._review_queue_workspace
            )
        return self._review_queue_workspace

    @Property(ProjectManagementProjectsWorkspaceController, constant=True)
    def projectsWorkspace(self) -> ProjectManagementProjectsWorkspaceController:
        return self._get_projects_workspace()

    @Property(ProjectManagementResourcesWorkspaceController, constant=True)
    def resourcesWorkspace(self) -> ProjectManagementResourcesWorkspaceController:
        return self._get_resources_workspace()

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

    @Property(ProjectManagementResourceTimesheetsController, constant=True)
    def timesheetsWorkspace(self) -> ProjectManagementResourceTimesheetsController:
        return self._get_timesheets_workspace()

    @Property(ProjectManagementTimesheetsWorkspaceController, constant=True)
    def reviewQueueWorkspace(self) -> ProjectManagementTimesheetsWorkspaceController:
        return self._get_review_queue_workspace()

    @Property(PMCapabilityController, constant=True)
    def pmCapabilityController(self) -> PMCapabilityController:
        return self._pm_capability

    @Property(PMWorkspaceNavigationController, constant=True)
    def pmNavigation(self) -> PMWorkspaceNavigationController:
        return self._pm_navigation

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

    @Slot()
    def refreshAllWorkspaces(self) -> None:
        self.refreshCapabilities()
        for controller in (
            self._projects_workspace,
            self._financials_workspace,
            self._portfolio_workspace,
            self._resources_workspace,
            self._register_workspace,
            self._scheduling_workspace,
            self._tasks_workspace,
            self._dashboard_workspace,
            self._collaboration_workspace,
            self._timesheets_workspace,
            self._review_queue_workspace,
        ):
            if controller is None:
                continue
            controller_refresh = getattr(controller, "refresh", None)
            if callable(controller_refresh):
                controller_refresh()

    @Slot()
    def refreshCapabilities(self) -> None:
        self._pm_capability.refresh()
        if self._approval_view_invalidation_adapter is not None:
            self._approval_view_invalidation_adapter.set_active_scope(
                tenant_id=self._active_tenant_id() or "",
                organization_id=self._active_organization_id() or "",
            )
        if self._employee_view_invalidation_adapter is not None:
            self._employee_view_invalidation_adapter.set_active_scope(
                tenant_id=self._active_tenant_id() or "",
                organization_id=self._active_organization_id() or "",
            )
        if self._forecast_view_invalidation_adapter is not None:
            self._forecast_view_invalidation_adapter.set_active_scope(
                tenant_id=self._active_tenant_id() or "",
                organization_id=self._active_organization_id() or "",
            )
        if self._financial_profile_view_invalidation_adapter is not None:
            self._financial_profile_view_invalidation_adapter.set_active_scope(
                tenant_id=self._active_tenant_id() or "",
                organization_id=self._active_organization_id() or "",
            )
        for resource_adapter in (
            self._resource_view_invalidation_adapter,
            self._portfolio_resource_view_invalidation_adapter,
            self._scheduling_resource_view_invalidation_adapter,
            self._tasks_resource_view_invalidation_adapter,
            self._dashboard_resource_view_invalidation_adapter,
            self._timesheets_resource_view_invalidation_adapter,
            self._review_queue_resource_view_invalidation_adapter,
        ):
            if resource_adapter is not None:
                resource_adapter.set_active_scope(
                    tenant_id=self._active_tenant_id() or "",
                    organization_id=self._active_organization_id() or "",
                )

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
