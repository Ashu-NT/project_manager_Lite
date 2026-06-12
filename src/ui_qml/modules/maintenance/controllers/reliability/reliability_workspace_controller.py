from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenanceReliabilityWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)
from .reliability_filter_actions import (
    apply_asset_filter,
    apply_days_filter,
    apply_failure_code_filter,
    apply_limit_filter,
    apply_location_filter,
    apply_site_filter,
    apply_system_filter,
    apply_threshold_filter,
)
from .reliability_state_loader import load_workspace_state

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

    @Slot(str)
    def setFailureCodeFilter(self, failure_code: str) -> None:
        apply_failure_code_filter(self, failure_code)

    @Slot(int)
    def setDaysFilter(self, days: int) -> None:
        apply_days_filter(self, days)

    @Slot(int)
    def setLimitFilter(self, limit: int) -> None:
        apply_limit_filter(self, limit)

    @Slot(int)
    def setThresholdFilter(self, threshold: int) -> None:
        apply_threshold_filter(self, threshold)

    # --- Domain event wiring ---

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="maintenance_management")
        self._subscribe_domain_change("site", scope_code="platform")


__all__ = ["MaintenanceReliabilityWorkspaceController"]
