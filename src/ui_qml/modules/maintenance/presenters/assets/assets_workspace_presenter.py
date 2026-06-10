from __future__ import annotations

from typing import Any

from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetsDesktopApi,
    build_maintenance_assets_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetsWorkspaceViewModel,
)

from .asset_command_handler import create_asset, toggle_asset_active, update_asset
from .code_generation import (
    suggest_asset_code,
    suggest_component_code,
    suggest_location_code,
    suggest_system_code,
)
from .component_command_handler import (
    create_component,
    toggle_component_active,
    update_component,
)
from .location_command_handler import (
    create_location,
    toggle_location_active,
    update_location,
)
from .system_command_handler import create_system, toggle_system_active, update_system
from .workspace_builder import build_workspace_state


class MaintenanceAssetsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenanceAssetsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_assets_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        site_filter: str = "all",
        active_filter: str = "all",
        selected_location_id: str | None = None,
        selected_system_id: str | None = None,
        selected_asset_id: str | None = None,
        selected_component_id: str | None = None,
    ) -> MaintenanceAssetsWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            search_text=search_text,
            site_filter=site_filter,
            active_filter=active_filter,
            selected_location_id=selected_location_id,
            selected_system_id=selected_system_id,
            selected_asset_id=selected_asset_id,
            selected_component_id=selected_component_id,
        )

    def suggest_location_code(self, payload: dict[str, Any]) -> str:
        return suggest_location_code(self._desktop_api, payload)

    def suggest_system_code(self, payload: dict[str, Any]) -> str:
        return suggest_system_code(self._desktop_api, payload)

    def suggest_asset_code(self, payload: dict[str, Any]) -> str:
        return suggest_asset_code(self._desktop_api, payload)

    def suggest_component_code(self, payload: dict[str, Any]) -> str:
        return suggest_component_code(self._desktop_api, payload)

    def create_location(self, payload: dict[str, Any]) -> None:
        create_location(self._desktop_api, payload)

    def update_location(self, payload: dict[str, Any]) -> None:
        update_location(self._desktop_api, payload)

    def toggle_location_active(self, location_id: str, *, expected_version: int) -> None:
        toggle_location_active(self._desktop_api, location_id, expected_version=expected_version)

    def create_system(self, payload: dict[str, Any]) -> None:
        create_system(self._desktop_api, payload)

    def update_system(self, payload: dict[str, Any]) -> None:
        update_system(self._desktop_api, payload)

    def toggle_system_active(self, system_id: str, *, expected_version: int) -> None:
        toggle_system_active(self._desktop_api, system_id, expected_version=expected_version)

    def create_asset(self, payload: dict[str, Any]) -> None:
        create_asset(self._desktop_api, payload)

    def update_asset(self, payload: dict[str, Any]) -> None:
        update_asset(self._desktop_api, payload)

    def toggle_asset_active(self, asset_id: str, *, expected_version: int) -> None:
        toggle_asset_active(self._desktop_api, asset_id, expected_version=expected_version)

    def create_component(self, payload: dict[str, Any]) -> None:
        create_component(self._desktop_api, payload)

    def update_component(self, payload: dict[str, Any]) -> None:
        update_component(self._desktop_api, payload)

    def toggle_component_active(self, component_id: str, *, expected_version: int) -> None:
        toggle_component_active(
            self._desktop_api, component_id, expected_version=expected_version
        )
