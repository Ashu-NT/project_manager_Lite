from __future__ import annotations

from PySide6.QtCore import Property, QObject, Slot

from src.api.desktop.platform import PlatformRuntimeDesktopApi
from src.ui_qml.platform.controllers.admin import (
    PlatformAdminAccessWorkspaceController,
    PlatformAdminWorkspaceController,
    PlatformSupportWorkspaceController,
)
from src.ui_qml.platform.controllers.control import PlatformControlWorkspaceController
from src.ui_qml.platform.controllers.settings import PlatformSettingsWorkspaceController
from src.ui_qml.platform.presenters import (
    PlatformAccessWorkspacePresenter,
    PlatformAdminWorkspacePresenter,
    PlatformControlQueuePresenter,
    PlatformControlWorkspacePresenter,
    PlatformDepartmentCatalogPresenter,
    PlatformDocumentCatalogPresenter,
    PlatformDocumentManagementPresenter,
    PlatformEmployeeCatalogPresenter,
    PlatformOrganizationCatalogPresenter,
    PlatformPartyCatalogPresenter,
    PlatformRuntimePresenter,
    PlatformSettingsCatalogPresenter,
    PlatformSettingsWorkspacePresenter,
    PlatformSiteCatalogPresenter,
    PlatformSupportWorkspacePresenter,
    PlatformUserCatalogPresenter,
)
from src.ui_qml.platform.routes import build_platform_routes


class PlatformWorkspaceCatalog(QObject):
    def __init__(
        self,
        desktop_api: PlatformRuntimeDesktopApi | None = None,
        desktop_api_registry: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        runtime_api = desktop_api
        if desktop_api_registry is not None:
            runtime_api = getattr(desktop_api_registry, "platform_runtime", None) or desktop_api
        self._runtime_presenter = PlatformRuntimePresenter(runtime_api)
        site_api = getattr(desktop_api_registry, "platform_site", None)
        department_api = getattr(desktop_api_registry, "platform_department", None)
        employee_api = getattr(desktop_api_registry, "platform_employee", None)
        user_api = getattr(desktop_api_registry, "platform_user", None)
        document_api = getattr(desktop_api_registry, "platform_document", None)
        party_api = getattr(desktop_api_registry, "platform_party", None)
        admin_overview_presenter = PlatformAdminWorkspacePresenter(
            runtime_api=runtime_api,
            site_api=site_api,
            department_api=department_api,
            employee_api=employee_api,
            user_api=user_api,
            document_api=document_api,
            party_api=party_api,
        )
        control_presenter = PlatformControlWorkspacePresenter(
            approval_api=getattr(desktop_api_registry, "platform_approval", None),
            audit_api=getattr(desktop_api_registry, "platform_audit", None),
        )
        control_queue_presenter = PlatformControlQueuePresenter(
            approval_api=getattr(desktop_api_registry, "platform_approval", None),
            audit_api=getattr(desktop_api_registry, "platform_audit", None),
        )
        settings_presenter = PlatformSettingsWorkspacePresenter(runtime_api=runtime_api)
        settings_catalog_presenter = PlatformSettingsCatalogPresenter(runtime_api=runtime_api)
        self._admin_workspace = PlatformAdminWorkspaceController(
            overview_presenter=admin_overview_presenter,
            organization_presenter=PlatformOrganizationCatalogPresenter(runtime_api=runtime_api),
            site_presenter=PlatformSiteCatalogPresenter(site_api=site_api),
            department_presenter=PlatformDepartmentCatalogPresenter(
                department_api=department_api,
                site_api=site_api,
            ),
            employee_presenter=PlatformEmployeeCatalogPresenter(
                employee_api=employee_api,
                site_api=site_api,
                department_api=department_api,
            ),
            user_presenter=PlatformUserCatalogPresenter(user_api=user_api),
            party_presenter=PlatformPartyCatalogPresenter(party_api=party_api),
            document_presenter=PlatformDocumentCatalogPresenter(document_api=document_api),
            document_management_presenter=PlatformDocumentManagementPresenter(document_api=document_api),
            parent=self,
        )
        self._admin_access_workspace = PlatformAdminAccessWorkspaceController(
            presenter=PlatformAccessWorkspacePresenter(
                access_api=getattr(desktop_api_registry, "platform_access", None),
                user_api=user_api,
            ),
            parent=self,
        )
        self._admin_support_workspace = PlatformSupportWorkspaceController(
            presenter=PlatformSupportWorkspacePresenter(
                support_api=getattr(desktop_api_registry, "platform_support", None),
            ),
            parent=self,
        )
        self._control_workspace = PlatformControlWorkspaceController(
            overview_presenter=control_presenter,
            queue_presenter=control_queue_presenter,
            parent=self,
        )
        self._settings_workspace = PlatformSettingsWorkspaceController(
            overview_presenter=settings_presenter,
            catalog_presenter=settings_catalog_presenter,
            parent=self,
        )
        self._route_by_id = {route.route_id: route for route in build_platform_routes()}

    @Property(PlatformAdminWorkspaceController, constant=True)
    def adminWorkspace(self) -> PlatformAdminWorkspaceController:
        return self._admin_workspace

    @Property(PlatformAdminAccessWorkspaceController, constant=True)
    def adminAccessWorkspace(self) -> PlatformAdminAccessWorkspaceController:
        return self._admin_access_workspace

    @Property(PlatformSupportWorkspaceController, constant=True)
    def adminSupportWorkspace(self) -> PlatformSupportWorkspaceController:
        return self._admin_support_workspace

    @Property(PlatformControlWorkspaceController, constant=True)
    def controlWorkspace(self) -> PlatformControlWorkspaceController:
        return self._control_workspace

    @Property(PlatformSettingsWorkspaceController, constant=True)
    def settingsWorkspace(self) -> PlatformSettingsWorkspaceController:
        return self._settings_workspace

    @Slot(str, result="QVariantMap")
    def workspace(self, route_id: str) -> dict[str, str]:
        route = self._route_by_id.get(route_id)
        if route is None:
            return {"routeId": route_id, "title": "", "summary": ""}
        return {
            "routeId": route.route_id,
            "title": route.title,
            "summary": f"{route.module_label} / {route.group_label}",
        }

    @Slot(result="QVariantMap")
    def runtimeOverview(self) -> dict[str, object]:
        overview = self._runtime_presenter.build_overview()
        return {
            "title": overview.title,
            "subtitle": overview.subtitle,
            "statusLabel": overview.status_label,
            "metrics": [
                {
                    "label": metric.label,
                    "value": metric.value,
                    "supportingText": metric.supporting_text,
                }
                for metric in overview.metrics
            ],
        }

    @Slot(result="QVariantMap")
    def adminOverview(self) -> dict[str, object]:
        return dict(self._admin_workspace.overview)

    @Slot(result="QVariantMap")
    def controlOverview(self) -> dict[str, object]:
        return dict(self._control_workspace.overview)

    @Slot(result="QVariantMap")
    def settingsOverview(self) -> dict[str, object]:
        return dict(self._settings_workspace.overview)

    @Slot(result="QVariantMap")
    def approvalQueue(self) -> dict[str, object]:
        return dict(self._control_workspace.approvalQueue)

    @Slot(result="QVariantMap")
    def auditFeed(self) -> dict[str, object]:
        return dict(self._control_workspace.auditFeed)

    @Slot(result="QVariantMap")
    def moduleEntitlements(self) -> dict[str, object]:
        return dict(self._settings_workspace.moduleEntitlements)

    @Slot(result="QVariantMap")
    def organizationProfiles(self) -> dict[str, object]:
        return dict(self._settings_workspace.organizationProfiles)

    @Slot(str, result="QVariantMap")
    def approveRequest(self, request_id: str) -> dict[str, object]:
        self._control_workspace.approveRequest(request_id)
        return dict(self._control_workspace.operationResult)

    @Slot(str, result="QVariantMap")
    def rejectRequest(self, request_id: str) -> dict[str, object]:
        self._control_workspace.rejectRequest(request_id)
        return dict(self._control_workspace.operationResult)

    @Slot(str, str, result="QVariantMap")
    def approveRequestWithNote(self, request_id: str, note: str) -> dict[str, object]:
        self._control_workspace.approveRequestWithNote(request_id, note)
        return dict(self._control_workspace.operationResult)

    @Slot(str, str, result="QVariantMap")
    def rejectRequestWithNote(self, request_id: str, note: str) -> dict[str, object]:
        self._control_workspace.rejectRequestWithNote(request_id, note)
        return dict(self._control_workspace.operationResult)

    @Slot(str, result="QVariantMap")
    def toggleModuleLicensed(self, module_code: str) -> dict[str, object]:
        self._settings_workspace.toggleModuleLicensed(module_code)
        return dict(self._settings_workspace.operationResult)

    @Slot(str, result="QVariantMap")
    def toggleModuleEnabled(self, module_code: str) -> dict[str, object]:
        self._settings_workspace.toggleModuleEnabled(module_code)
        return dict(self._settings_workspace.operationResult)

    @Slot(str, str, result="QVariantMap")
    def changeModuleLifecycleStatus(self, module_code: str, lifecycle_status: str) -> dict[str, object]:
        self._settings_workspace.changeModuleLifecycleStatus(module_code, lifecycle_status)
        return dict(self._settings_workspace.operationResult)


__all__ = ["PlatformWorkspaceCatalog"]
