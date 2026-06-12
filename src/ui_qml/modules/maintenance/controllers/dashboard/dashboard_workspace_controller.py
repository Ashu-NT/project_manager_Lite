from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenanceDashboardWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)
from .dashboard_filter_actions import (
    apply_asset_filter,
    apply_days_filter,
    apply_location_filter,
    apply_site_filter,
    apply_system_filter,
)
from .dashboard_state_loader import load_workspace_state

QML_IMPORT_NAME = "Maintenance.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Maintenance workspace controllers are provided by the shell runtime.")
class MaintenanceDashboardWorkspaceController(MaintenanceWorkspaceControllerBase):
    overviewChanged = Signal()
    siteOptionsChanged = Signal()
    assetOptionsChanged = Signal()
    systemOptionsChanged = Signal()
    locationOptionsChanged = Signal()
    windowOptionsChanged = Signal()
    selectedSiteFilterChanged = Signal()
    selectedAssetFilterChanged = Signal()
    selectedSystemFilterChanged = Signal()
    selectedLocationFilterChanged = Signal()
    selectedDaysFilterChanged = Signal()
    backlogRowsChanged = Signal()
    rootCauseRowsChanged = Signal()
    recurringRowsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: MaintenanceWorkspacePresenter | None = None,
        dashboard_workspace_presenter: MaintenanceDashboardWorkspacePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or MaintenanceWorkspacePresenter(
            "maintenance_management.dashboard"
        )
        self._dashboard_workspace_presenter = (
            dashboard_workspace_presenter or MaintenanceDashboardWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._site_options: list[dict[str, object]] = []
        self._asset_options: list[dict[str, object]] = []
        self._system_options: list[dict[str, object]] = []
        self._location_options: list[dict[str, object]] = []
        self._window_options: list[dict[str, object]] = []
        self._selected_site_filter = "all"
        self._selected_asset_filter = "all"
        self._selected_system_filter = "all"
        self._selected_location_filter = "all"
        self._selected_days_filter = "90"
        self._backlog_rows: list[dict[str, object]] = []
        self._root_cause_rows: list[dict[str, object]] = []
        self._recurring_rows: list[dict[str, object]] = []
        self._bind_domain_events()
        self.refresh()

    # --- Qt Properties ---

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=siteOptionsChanged)
    def siteOptions(self) -> list[dict[str, object]]:
        return self._site_options

    @Property("QVariantList", notify=assetOptionsChanged)
    def assetOptions(self) -> list[dict[str, object]]:
        return self._asset_options

    @Property("QVariantList", notify=systemOptionsChanged)
    def systemOptions(self) -> list[dict[str, object]]:
        return self._system_options

    @Property("QVariantList", notify=locationOptionsChanged)
    def locationOptions(self) -> list[dict[str, object]]:
        return self._location_options

    @Property("QVariantList", notify=windowOptionsChanged)
    def windowOptions(self) -> list[dict[str, object]]:
        return self._window_options

    @Property(str, notify=selectedSiteFilterChanged)
    def selectedSiteFilter(self) -> str:
        return self._selected_site_filter

    @Property(str, notify=selectedAssetFilterChanged)
    def selectedAssetFilter(self) -> str:
        return self._selected_asset_filter

    @Property(str, notify=selectedSystemFilterChanged)
    def selectedSystemFilter(self) -> str:
        return self._selected_system_filter

    @Property(str, notify=selectedLocationFilterChanged)
    def selectedLocationFilter(self) -> str:
        return self._selected_location_filter

    @Property(str, notify=selectedDaysFilterChanged)
    def selectedDaysFilter(self) -> str:
        return self._selected_days_filter

    @Property("QVariantList", notify=backlogRowsChanged)
    def backlogRows(self) -> list[dict[str, object]]:
        return self._backlog_rows

    @Property("QVariantList", notify=rootCauseRowsChanged)
    def rootCauseRows(self) -> list[dict[str, object]]:
        return self._root_cause_rows

    @Property("QVariantList", notify=recurringRowsChanged)
    def recurringRows(self) -> list[dict[str, object]]:
        return self._recurring_rows

    # --- Slots ---

    @Slot()
    def refresh(self) -> None:
        load_workspace_state(self)

    @Slot(str)
    def setSiteFilter(self, site_id: str) -> None:
        apply_site_filter(self, site_id)

    @Slot(str)
    def setAssetFilter(self, asset_id: str) -> None:
        apply_asset_filter(self, asset_id)

    @Slot(str)
    def setSystemFilter(self, system_id: str) -> None:
        apply_system_filter(self, system_id)

    @Slot(str)
    def setLocationFilter(self, location_id: str) -> None:
        apply_location_filter(self, location_id)

    @Slot(int)
    def setDaysFilter(self, days: int) -> None:
        apply_days_filter(self, days)

    # --- Domain event wiring ---

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="maintenance_management")
        self._subscribe_domain_change("site", scope_code="platform")


__all__ = ["MaintenanceDashboardWorkspaceController"]
