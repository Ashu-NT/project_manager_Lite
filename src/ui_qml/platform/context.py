from __future__ import annotations

from PySide6.QtCore import QObject, Slot

from src.api.desktop.platform import PlatformRuntimeDesktopApi
from src.ui_qml.platform.presenters import PlatformRuntimePresenter
from src.ui_qml.platform.routes import build_platform_routes


class PlatformWorkspaceCatalog(QObject):
    def __init__(
        self,
        desktop_api: PlatformRuntimeDesktopApi | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._runtime_presenter = PlatformRuntimePresenter(desktop_api)
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


__all__ = ["PlatformWorkspaceCatalog"]
