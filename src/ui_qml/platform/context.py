from __future__ import annotations

from PySide6.QtCore import QObject, Slot

from src.api.desktop.platform import PlatformRuntimeDesktopApi
from src.ui_qml.platform.presenters import (
    PlatformAdminWorkspacePresenter,
    PlatformControlWorkspacePresenter,
    PlatformRuntimePresenter,
    PlatformSettingsWorkspacePresenter,
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
        self._admin_presenter = PlatformAdminWorkspacePresenter(
            runtime_api=runtime_api,
            site_api=getattr(desktop_api_registry, "platform_site", None),
            department_api=getattr(desktop_api_registry, "platform_department", None),
            employee_api=getattr(desktop_api_registry, "platform_employee", None),
            user_api=getattr(desktop_api_registry, "platform_user", None),
            document_api=getattr(desktop_api_registry, "platform_document", None),
            party_api=getattr(desktop_api_registry, "platform_party", None),
        )
        self._control_presenter = PlatformControlWorkspacePresenter(
            approval_api=getattr(desktop_api_registry, "platform_approval", None),
            audit_api=getattr(desktop_api_registry, "platform_audit", None),
        )
        self._settings_presenter = PlatformSettingsWorkspacePresenter(runtime_api=runtime_api)
        self._route_by_id = {route.route_id: route for route in build_platform_routes()}

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
        return self._serialize_workspace_overview(self._admin_presenter.build_overview())

    @Slot(result="QVariantMap")
    def controlOverview(self) -> dict[str, object]:
        return self._serialize_workspace_overview(self._control_presenter.build_overview())

    @Slot(result="QVariantMap")
    def settingsOverview(self) -> dict[str, object]:
        return self._serialize_workspace_overview(self._settings_presenter.build_overview())

    @staticmethod
    def _serialize_workspace_overview(overview) -> dict[str, object]:
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
            "sections": [
                {
                    "title": section.title,
                    "emptyState": section.empty_state,
                    "rows": [
                        {
                            "label": row.label,
                            "value": row.value,
                            "supportingText": row.supporting_text,
                        }
                        for row in section.rows
                    ],
                }
                for section in overview.sections
            ],
        }


__all__ = ["PlatformWorkspaceCatalog"]
