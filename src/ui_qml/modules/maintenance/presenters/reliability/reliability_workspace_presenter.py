from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceReliabilityDesktopApi,
    build_maintenance_reliability_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.reliability import (
    MaintenanceReliabilityWorkspaceViewModel,
)

from .workspace_builder import build_workspace_state


class MaintenanceReliabilityWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenanceReliabilityDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_reliability_desktop_api()

    def build_workspace_state(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        failure_code: str | None = None,
        days: int = 90,
        limit: int = 20,
        threshold: int = 2,
    ) -> MaintenanceReliabilityWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            site_id=site_id,
            asset_id=asset_id,
            system_id=system_id,
            location_id=location_id,
            failure_code=failure_code,
            days=days,
            limit=limit,
            threshold=threshold,
        )


__all__ = ["MaintenanceReliabilityWorkspacePresenter"]
