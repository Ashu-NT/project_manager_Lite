from __future__ import annotations

from PySide6.QtCore import Property, QObject, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.core.platform.api.desktop.integration import IntegrationCapabilityDesktopApi
from src.core.platform.api.desktop.platform_runtime.runtime import PlatformRuntimeDesktopApi
from src.ui_qml.platform.adapters.module_entitlement_view_invalidation_adapter import (
    ModuleEntitlementViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.organization_view_invalidation_adapter import (
    OrganizationViewInvalidationAdapter,
)
from src.ui_qml.platform.controllers.admin_console import PlatformAdminWorkspaceController
from src.ui_qml.platform.controllers.identity_access.access import (
    PlatformAdminAccessWorkspaceController,
)
from src.ui_qml.platform.controllers.support import PlatformSupportWorkspaceController
from src.ui_qml.platform.controllers.control import PlatformControlWorkspaceController
from src.ui_qml.platform.controllers.settings import PlatformSettingsWorkspaceController
from src.ui_qml.platform.controllers.tenants import TenantSwitcherController
from src.ui_qml.platform.presenters import (
    PlatformAccessWorkspacePresenter,
    PlatformAdminWorkspacePresenter,
    PlatformControlQueuePresenter,
    PlatformControlWorkspacePresenter,
    PlatformCalendarCatalogPresenter,
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
    TenantSwitcherPresenter,
    PlatformUserCatalogPresenter,
)
from src.ui_qml.platform.routes import build_platform_routes

QML_IMPORT_NAME = "Platform.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Platform workspace catalogs are provided by the shell runtime.")
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
        self._runtime_api = runtime_api
        self._current_permissions: frozenset[str] = frozenset()
        self._reload_current_permissions()
        self._integration_api: IntegrationCapabilityDesktopApi | None = (
            getattr(desktop_api_registry, "integration_capability", None)
            if desktop_api_registry is not None
            else None
        )
        self._runtime_presenter = PlatformRuntimePresenter(runtime_api)
        site_api = getattr(desktop_api_registry, "platform_site", None)
        calendar_api = getattr(desktop_api_registry, "platform_calendar", None)
        enterprise_calendar_api = getattr(desktop_api_registry, "platform_enterprise_calendar", None)
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
            audit_api=getattr(desktop_api_registry, "platform_enterprise_audit", None),
        )
        control_queue_presenter = PlatformControlQueuePresenter(
            approval_api=getattr(desktop_api_registry, "platform_approval", None),
            audit_api=getattr(desktop_api_registry, "platform_enterprise_audit", None),
        )
        settings_presenter = PlatformSettingsWorkspacePresenter(runtime_api=runtime_api)
        settings_catalog_presenter = PlatformSettingsCatalogPresenter(
            runtime_api=runtime_api,
            integration_api=self._integration_api,
        )
        self._admin_workspace = PlatformAdminWorkspaceController(
            overview_presenter=admin_overview_presenter,
            organization_presenter=PlatformOrganizationCatalogPresenter(runtime_api=runtime_api),
            calendar_presenter=PlatformCalendarCatalogPresenter(
                calendar_api=calendar_api,
                enterprise_calendar_api=enterprise_calendar_api,
            ),
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
            enterprise_calendar_api=enterprise_calendar_api,
            runtime_api=runtime_api,
            parent=self,
        )
        self._admin_access_workspace = PlatformAdminAccessWorkspaceController(
            presenter=PlatformAccessWorkspacePresenter(
                access_api=getattr(desktop_api_registry, "platform_access", None),
                user_api=user_api,
            ),
            runtime_api=runtime_api,
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
            runtime_api=runtime_api,
            parent=self,
        )
        self._settings_workspace = PlatformSettingsWorkspaceController(
            overview_presenter=settings_presenter,
            catalog_presenter=settings_catalog_presenter,
            runtime_api=runtime_api,
            parent=self,
        )
        tenant_api = getattr(desktop_api_registry, "platform_tenant", None) if desktop_api_registry is not None else None
        self._tenant_switcher = TenantSwitcherController(
            TenantSwitcherPresenter(tenant_api=tenant_api),
            self,
        )
        self._tenant_switcher.refresh()
        self._route_by_id = {route.route_id: route for route in build_platform_routes()}

        # P5A + Organization-specific P6A cutover: the two real Organization-creation UI
        # consumers (admin console organization list, settings organization profiles list) react
        # to the typed OrganizationCreated event via this Qt adapter, never the legacy
        # organizations_changed signal -- which remains wired, unchanged, for
        # update/activation-triggered refreshes only.
        view_invalidation_channel = (
            getattr(desktop_api_registry, "platform_view_invalidation_channel", None)
            if desktop_api_registry is not None
            else None
        )
        self._organization_view_invalidation_adapter = OrganizationViewInvalidationAdapter(
            channel=view_invalidation_channel,
            tenant_id=self._tenant_switcher.activeTenantId,
            parent=self,
        )
        self._organization_view_invalidation_adapter.organizationCollectionStale.connect(
            self._admin_workspace.refresh_organizations
        )
        self._organization_view_invalidation_adapter.organizationCollectionStale.connect(
            self._settings_workspace.refresh_organization_profiles
        )
        # Tenant-scope hardening: a single adapter instance persists across a tenant switch (the
        # QML controller tree is never reconstructed), so it must be re-scoped to whichever
        # tenant is now active -- otherwise it would keep matching the PREVIOUS tenant's
        # organization-collection invalidations (or, with the earlier AllTenants() subscription,
        # every tenant's), never correctly following the switch.
        self._tenant_switcher.tenantSwitched.connect(self._on_tenant_switched)

        # P5B-3: direct Qt cutover for Module Entitlements, mirroring the Organization precedent
        # above -- no legacy `modules_changed` bridge. Organization-scoped
        # (`ExactOrganization(tenant_id, organization_id)`, never tenant-wide), so it must follow
        # BOTH a tenant switch and an organization switch -- re-scoped via
        # `refreshCurrentPermissions()`, the existing hook the QML shell already calls
        # immediately after either (`PlatformWorkspacePage.qml`'s `ContextBar.onTenantSelected`/
        # `onOrganizationSelected`), since this desktop shell has no separate, dedicated
        # "organization switched" Qt signal the way `TenantSwitcherController.tenantSwitched`
        # exists for tenants. Only the settings workspace's `moduleEntitlements` list is a real
        # consumer here -- tracing the other two former `modules_changed` subscribers (control,
        # access) end-to-end found neither reads any module-entitlement-derived state, so neither
        # is migrated (see the P5B-3 report).
        self._module_entitlement_view_invalidation_adapter = ModuleEntitlementViewInvalidationAdapter(
            channel=view_invalidation_channel,
            tenant_id=self._tenant_switcher.activeTenantId,
            organization_id=self._active_organization_id(),
            parent=self,
        )
        self._module_entitlement_view_invalidation_adapter.moduleEntitlementsStale.connect(
            self._settings_workspace.refresh_module_entitlements
        )

    def _on_tenant_switched(self) -> None:
        self._organization_view_invalidation_adapter.set_active_tenant(
            self._tenant_switcher.activeTenantId
        )

    def _active_organization_id(self) -> str:
        if self._runtime_api is None:
            return ""
        result = self._runtime_api.get_runtime_context()
        if not result.ok or result.data is None or result.data.active_organization is None:
            return ""
        return result.data.active_organization.id

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

    @Property(TenantSwitcherController, constant=True)
    def tenantSwitcher(self) -> TenantSwitcherController:
        return self._tenant_switcher

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

    @Slot()
    def refreshAllWorkspaces(self) -> None:
        for controller in (
            self._tenant_switcher,
            self._admin_workspace,
            self._admin_access_workspace,
            self._admin_support_workspace,
            self._control_workspace,
            self._settings_workspace,
        ):
            if not getattr(controller, "_loaded", True):
                continue
            refresh = getattr(controller, "refresh", None)
            if callable(refresh):
                refresh()

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

    # ------------------------------------------------------------------
    # RBAC visibility slots — used by the shell nav and workspace pages to
    # hide destinations/actions the current user has no backend permission
    # for, instead of showing them and letting the desktop-API call fail.
    # ------------------------------------------------------------------

    def _reload_current_permissions(self) -> None:
        if self._runtime_api is None:
            self._current_permissions = frozenset()
            return
        result = self._runtime_api.get_current_permissions()
        if not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            self._current_permissions = frozenset()
            return
        self._current_permissions = frozenset(result.data)

    @Slot()
    def refreshCurrentPermissions(self) -> None:
        """Call after a tenant/organization switch or re-authentication so
        nav/action visibility reflects the new session's actual authority.

        P5B-3: also the re-scoping hook for `ModuleEntitlementViewInvalidationAdapter` -- this
        desktop shell has no dedicated "organization switched" Qt signal the way
        `TenantSwitcherController.tenantSwitched` exists for tenants, but the QML shell already
        calls this method immediately after BOTH a tenant switch and an organization switch
        (`PlatformWorkspacePage.qml`'s `ContextBar.onTenantSelected`/`onOrganizationSelected`), so
        re-scoping here correctly follows either kind of switch."""
        self._reload_current_permissions()
        self._module_entitlement_view_invalidation_adapter.set_active_scope(
            tenant_id=self._tenant_switcher.activeTenantId,
            organization_id=self._active_organization_id(),
        )

    @Slot(str, result=bool)
    def hasPermission(self, permission_code: str) -> bool:
        return permission_code in self._current_permissions

    @Slot("QVariantList", result=bool)
    def hasAnyPermission(self, permission_codes: list) -> bool:
        return any(code in self._current_permissions for code in permission_codes)

    # ------------------------------------------------------------------
    # Module capability slots — used by all QML workspaces to gate
    # cross-module actions without importing optional module code.
    # ------------------------------------------------------------------

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

    @Slot(str, str, str, str, str, str, result="QVariantMap")
    def resolveSoftReference(
        self,
        source_module: str,
        source_entity_type: str,
        source_entity_id: str,
        source_code_snapshot: str = "",
        source_title_snapshot: str = "",
        source_status_snapshot: str = "",
    ) -> dict:
        if self._integration_api is None:
            return {
                "canOpen": False,
                "disabledReason": "Integration layer not available",
                "displayTitle": source_title_snapshot or source_code_snapshot,
                "displaySubtitle": "",
                "displayStatus": source_status_snapshot,
                "route": None,
                "moduleEnabled": False,
                "sourceAvailable": False,
            }
        return self._integration_api.resolve_soft_reference(
            source_module or None,
            source_entity_type or None,
            source_entity_id or None,
            source_code_snapshot or None,
            source_title_snapshot or None,
            source_status_snapshot or None,
        )


__all__ = ["PlatformWorkspaceCatalog"]
