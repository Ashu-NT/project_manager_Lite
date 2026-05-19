from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
    serialize_reliability_workspace_state,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenanceReliabilityWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)

QML_IMPORT_NAME = "Maintenance.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Maintenance workspace controllers are provided by the shell runtime.")
class MaintenanceReliabilityWorkspaceController(MaintenanceWorkspaceControllerBase):
    overviewChanged = Signal()
    siteOptionsChanged = Signal()
    assetOptionsChanged = Signal()
    systemOptionsChanged = Signal()
    locationOptionsChanged = Signal()
    failureSymptomOptionsChanged = Signal()
    daysOptionsChanged = Signal()
    limitOptionsChanged = Signal()
    thresholdOptionsChanged = Signal()
    selectedSiteFilterChanged = Signal()
    selectedAssetFilterChanged = Signal()
    selectedSystemFilterChanged = Signal()
    selectedLocationFilterChanged = Signal()
    selectedFailureCodeFilterChanged = Signal()
    selectedDaysFilterChanged = Signal()
    selectedLimitFilterChanged = Signal()
    selectedThresholdFilterChanged = Signal()
    suggestionRowsChanged = Signal()
    rootCauseRowsChanged = Signal()
    recurringRowsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: MaintenanceWorkspacePresenter | None = None,
        reliability_workspace_presenter: MaintenanceReliabilityWorkspacePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or MaintenanceWorkspacePresenter(
            "maintenance_management.reliability"
        )
        self._reliability_workspace_presenter = (
            reliability_workspace_presenter
            or MaintenanceReliabilityWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._site_options: list[dict[str, object]] = []
        self._asset_options: list[dict[str, object]] = []
        self._system_options: list[dict[str, object]] = []
        self._location_options: list[dict[str, object]] = []
        self._failure_symptom_options: list[dict[str, object]] = []
        self._days_options: list[dict[str, object]] = []
        self._limit_options: list[dict[str, object]] = []
        self._threshold_options: list[dict[str, object]] = []
        self._selected_site_filter = "all"
        self._selected_asset_filter = "all"
        self._selected_system_filter = "all"
        self._selected_location_filter = "all"
        self._selected_failure_code_filter = "all"
        self._selected_days_filter = "90"
        self._selected_limit_filter = "20"
        self._selected_threshold_filter = "2"
        self._suggestion_rows: list[dict[str, object]] = []
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

    @Property("QVariantList", notify=failureSymptomOptionsChanged)
    def failureSymptomOptions(self) -> list[dict[str, object]]:
        return self._failure_symptom_options

    @Property("QVariantList", notify=daysOptionsChanged)
    def daysOptions(self) -> list[dict[str, object]]:
        return self._days_options

    @Property("QVariantList", notify=limitOptionsChanged)
    def limitOptions(self) -> list[dict[str, object]]:
        return self._limit_options

    @Property("QVariantList", notify=thresholdOptionsChanged)
    def thresholdOptions(self) -> list[dict[str, object]]:
        return self._threshold_options

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

    @Property(str, notify=selectedFailureCodeFilterChanged)
    def selectedFailureCodeFilter(self) -> str:
        return self._selected_failure_code_filter

    @Property(str, notify=selectedDaysFilterChanged)
    def selectedDaysFilter(self) -> str:
        return self._selected_days_filter

    @Property(str, notify=selectedLimitFilterChanged)
    def selectedLimitFilter(self) -> str:
        return self._selected_limit_filter

    @Property(str, notify=selectedThresholdFilterChanged)
    def selectedThresholdFilter(self) -> str:
        return self._selected_threshold_filter

    @Property("QVariantList", notify=suggestionRowsChanged)
    def suggestionRows(self) -> list[dict[str, object]]:
        return self._suggestion_rows

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
            state = serialize_reliability_workspace_state(
                self._reliability_workspace_presenter.build_workspace_state(
                    site_id=self._normalized_filter(self._selected_site_filter),
                    asset_id=self._normalized_filter(self._selected_asset_filter),
                    system_id=self._normalized_filter(self._selected_system_filter),
                    location_id=self._normalized_filter(self._selected_location_filter),
                    failure_code=self._normalized_filter(
                        self._selected_failure_code_filter
                    ),
                    days=self._int_filter(self._selected_days_filter, 90),
                    limit=self._int_filter(self._selected_limit_filter, 20),
                    threshold=self._int_filter(self._selected_threshold_filter, 2),
                )
            )
            self._set_overview(state["overview"])
            self._set_site_options(state["siteOptions"])
            self._set_asset_options(state["assetOptions"])
            self._set_system_options(state["systemOptions"])
            self._set_location_options(state["locationOptions"])
            self._set_failure_symptom_options(state["failureSymptomOptions"])
            self._set_days_options(state["daysOptions"])
            self._set_limit_options(state["limitOptions"])
            self._set_threshold_options(state["thresholdOptions"])
            self._set_selected_site_filter(str(state["selectedSiteFilter"]))
            self._set_selected_asset_filter(str(state["selectedAssetFilter"]))
            self._set_selected_system_filter(str(state["selectedSystemFilter"]))
            self._set_selected_location_filter(str(state["selectedLocationFilter"]))
            self._set_selected_failure_code_filter(
                str(state["selectedFailureCodeFilter"])
            )
            self._set_selected_days_filter(str(state["selectedDaysFilter"]))
            self._set_selected_limit_filter(str(state["selectedLimitFilter"]))
            self._set_selected_threshold_filter(str(state["selectedThresholdFilter"]))
            self._set_suggestion_rows(state["suggestionRows"])
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

    @Slot(str)
    def setFailureCodeFilter(self, failure_code: str) -> None:
        self._set_selected_failure_code_filter(failure_code or "all")
        self.refresh()

    @Slot(int)
    def setDaysFilter(self, days: int) -> None:
        self._set_selected_days_filter(str(days))
        self.refresh()

    @Slot(int)
    def setLimitFilter(self, limit: int) -> None:
        self._set_selected_limit_filter(str(limit))
        self.refresh()

    @Slot(int)
    def setThresholdFilter(self, threshold: int) -> None:
        self._set_selected_threshold_filter(str(threshold))
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

    def _set_failure_symptom_options(self, options: list[dict[str, object]]) -> None:
        if options == self._failure_symptom_options:
            return
        self._failure_symptom_options = options
        self.failureSymptomOptionsChanged.emit()

    def _set_days_options(self, options: list[dict[str, object]]) -> None:
        if options == self._days_options:
            return
        self._days_options = options
        self.daysOptionsChanged.emit()

    def _set_limit_options(self, options: list[dict[str, object]]) -> None:
        if options == self._limit_options:
            return
        self._limit_options = options
        self.limitOptionsChanged.emit()

    def _set_threshold_options(self, options: list[dict[str, object]]) -> None:
        if options == self._threshold_options:
            return
        self._threshold_options = options
        self.thresholdOptionsChanged.emit()

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

    def _set_selected_failure_code_filter(self, value: str) -> None:
        value = value or "all"
        if value == self._selected_failure_code_filter:
            return
        self._selected_failure_code_filter = value
        self.selectedFailureCodeFilterChanged.emit()

    def _set_selected_days_filter(self, value: str) -> None:
        value = value or "90"
        if value == self._selected_days_filter:
            return
        self._selected_days_filter = value
        self.selectedDaysFilterChanged.emit()

    def _set_selected_limit_filter(self, value: str) -> None:
        value = value or "20"
        if value == self._selected_limit_filter:
            return
        self._selected_limit_filter = value
        self.selectedLimitFilterChanged.emit()

    def _set_selected_threshold_filter(self, value: str) -> None:
        value = value or "2"
        if value == self._selected_threshold_filter:
            return
        self._selected_threshold_filter = value
        self.selectedThresholdFilterChanged.emit()

    def _set_suggestion_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._suggestion_rows:
            return
        self._suggestion_rows = rows
        self.suggestionRowsChanged.emit()

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


__all__ = ["MaintenanceReliabilityWorkspaceController"]
