from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot

from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
    serialize_dashboard_workspace_state,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenanceDashboardWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)


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

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
            state = serialize_dashboard_workspace_state(
                self._dashboard_workspace_presenter.build_workspace_state(
                    site_id=self._normalized_filter(self._selected_site_filter),
                    asset_id=self._normalized_filter(self._selected_asset_filter),
                    system_id=self._normalized_filter(self._selected_system_filter),
                    location_id=self._normalized_filter(self._selected_location_filter),
                    days=self._int_filter(self._selected_days_filter, 90),
                )
            )
            self._set_overview(state["overview"])
            self._set_site_options(state["siteOptions"])
            self._set_asset_options(state["assetOptions"])
            self._set_system_options(state["systemOptions"])
            self._set_location_options(state["locationOptions"])
            self._set_window_options(state["windowOptions"])
            self._set_selected_site_filter(str(state["selectedSiteFilter"]))
            self._set_selected_asset_filter(str(state["selectedAssetFilter"]))
            self._set_selected_system_filter(str(state["selectedSystemFilter"]))
            self._set_selected_location_filter(str(state["selectedLocationFilter"]))
            self._set_selected_days_filter(str(state["selectedDaysFilter"]))
            self._set_backlog_rows(state["backlogRows"])
            self._set_root_cause_rows(state["rootCauseRows"])
            self._set_recurring_rows(state["recurringRows"])
            self._set_empty_state(str(state["emptyState"]))
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def setSiteFilter(self, site_id: str) -> None:
        self._set_selected_site_filter(site_id or "all")
        self.refresh()

    @Slot(str)
    def setAssetFilter(self, asset_id: str) -> None:
        self._set_selected_asset_filter(asset_id or "all")
        self.refresh()

    @Slot(str)
    def setSystemFilter(self, system_id: str) -> None:
        self._set_selected_system_filter(system_id or "all")
        self.refresh()

    @Slot(str)
    def setLocationFilter(self, location_id: str) -> None:
        self._set_selected_location_filter(location_id or "all")
        self.refresh()

    @Slot(int)
    def setDaysFilter(self, days: int) -> None:
        self._set_selected_days_filter(str(days))
        self.refresh()

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="maintenance_management")
        self._subscribe_domain_change("site", scope_code="platform")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_site_options(self, options: list[dict[str, object]]) -> None:
        if options == self._site_options:
            return
        self._site_options = options
        self.siteOptionsChanged.emit()

    def _set_asset_options(self, options: list[dict[str, object]]) -> None:
        if options == self._asset_options:
            return
        self._asset_options = options
        self.assetOptionsChanged.emit()

    def _set_system_options(self, options: list[dict[str, object]]) -> None:
        if options == self._system_options:
            return
        self._system_options = options
        self.systemOptionsChanged.emit()

    def _set_location_options(self, options: list[dict[str, object]]) -> None:
        if options == self._location_options:
            return
        self._location_options = options
        self.locationOptionsChanged.emit()

    def _set_window_options(self, options: list[dict[str, object]]) -> None:
        if options == self._window_options:
            return
        self._window_options = options
        self.windowOptionsChanged.emit()

    def _set_selected_site_filter(self, value: str) -> None:
        value = value or "all"
        if value == self._selected_site_filter:
            return
        self._selected_site_filter = value
        self.selectedSiteFilterChanged.emit()

    def _set_selected_asset_filter(self, value: str) -> None:
        value = value or "all"
        if value == self._selected_asset_filter:
            return
        self._selected_asset_filter = value
        self.selectedAssetFilterChanged.emit()

    def _set_selected_system_filter(self, value: str) -> None:
        value = value or "all"
        if value == self._selected_system_filter:
            return
        self._selected_system_filter = value
        self.selectedSystemFilterChanged.emit()

    def _set_selected_location_filter(self, value: str) -> None:
        value = value or "all"
        if value == self._selected_location_filter:
            return
        self._selected_location_filter = value
        self.selectedLocationFilterChanged.emit()

    def _set_selected_days_filter(self, value: str) -> None:
        value = value or "90"
        if value == self._selected_days_filter:
            return
        self._selected_days_filter = value
        self.selectedDaysFilterChanged.emit()

    def _set_backlog_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._backlog_rows:
            return
        self._backlog_rows = rows
        self.backlogRowsChanged.emit()

    def _set_root_cause_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._root_cause_rows:
            return
        self._root_cause_rows = rows
        self.rootCauseRowsChanged.emit()

    def _set_recurring_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._recurring_rows:
            return
        self._recurring_rows = rows
        self.recurringRowsChanged.emit()

    @staticmethod
    def _normalized_filter(value: str) -> str | None:
        normalized = str(value or "").strip()
        return "" if normalized in {"", "all"} else normalized

    @staticmethod
    def _int_filter(value: str, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


__all__ = ["MaintenanceDashboardWorkspaceController"]
