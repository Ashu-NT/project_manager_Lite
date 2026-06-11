from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenancePlannerWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)
from .planner_filter_actions import (
    apply_asset_filter,
    apply_request_queue,
    apply_search_text,
    apply_site_filter,
    apply_system_filter,
    apply_work_order_queue,
)
from .planner_state_loader import load_workspace_state

QML_IMPORT_NAME = "Maintenance.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Maintenance workspace controllers are provided by the shell runtime.")
class MaintenancePlannerWorkspaceController(MaintenanceWorkspaceControllerBase):
    overviewChanged = Signal()
    siteOptionsChanged = Signal()
    assetOptionsChanged = Signal()
    systemOptionsChanged = Signal()
    requestQueueOptionsChanged = Signal()
    workOrderQueueOptionsChanged = Signal()
    selectedSiteFilterChanged = Signal()
    selectedAssetFilterChanged = Signal()
    selectedSystemFilterChanged = Signal()
    selectedRequestQueueChanged = Signal()
    selectedWorkOrderQueueChanged = Signal()
    searchTextChanged = Signal()
    requestRowsChanged = Signal()
    workOrderRowsChanged = Signal()
    materialRowsChanged = Signal()
    preventiveRowsChanged = Signal()
    recurringRowsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: MaintenanceWorkspacePresenter | None = None,
        planner_workspace_presenter: MaintenancePlannerWorkspacePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or MaintenanceWorkspacePresenter(
            "maintenance_management.planner"
        )
        self._planner_workspace_presenter = (
            planner_workspace_presenter or MaintenancePlannerWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._site_options: list[dict[str, object]] = []
        self._asset_options: list[dict[str, object]] = []
        self._system_options: list[dict[str, object]] = []
        self._request_queue_options: list[dict[str, object]] = []
        self._work_order_queue_options: list[dict[str, object]] = []
        self._selected_site_filter = "all"
        self._selected_asset_filter = "all"
        self._selected_system_filter = "all"
        self._selected_request_queue = ""
        self._selected_work_order_queue = ""
        self._search_text = ""
        self._request_rows: list[dict[str, object]] = []
        self._work_order_rows: list[dict[str, object]] = []
        self._material_rows: list[dict[str, object]] = []
        self._preventive_rows: list[dict[str, object]] = []
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

    @Property("QVariantList", notify=requestQueueOptionsChanged)
    def requestQueueOptions(self) -> list[dict[str, object]]:
        return self._request_queue_options

    @Property("QVariantList", notify=workOrderQueueOptionsChanged)
    def workOrderQueueOptions(self) -> list[dict[str, object]]:
        return self._work_order_queue_options

    @Property(str, notify=selectedSiteFilterChanged)
    def selectedSiteFilter(self) -> str:
        return self._selected_site_filter

    @Property(str, notify=selectedAssetFilterChanged)
    def selectedAssetFilter(self) -> str:
        return self._selected_asset_filter

    @Property(str, notify=selectedSystemFilterChanged)
    def selectedSystemFilter(self) -> str:
        return self._selected_system_filter

    @Property(str, notify=selectedRequestQueueChanged)
    def selectedRequestQueue(self) -> str:
        return self._selected_request_queue

    @Property(str, notify=selectedWorkOrderQueueChanged)
    def selectedWorkOrderQueue(self) -> str:
        return self._selected_work_order_queue

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantList", notify=requestRowsChanged)
    def requestRows(self) -> list[dict[str, object]]:
        return self._request_rows

    @Property("QVariantList", notify=workOrderRowsChanged)
    def workOrderRows(self) -> list[dict[str, object]]:
        return self._work_order_rows

    @Property("QVariantList", notify=materialRowsChanged)
    def materialRows(self) -> list[dict[str, object]]:
        return self._material_rows

    @Property("QVariantList", notify=preventiveRowsChanged)
    def preventiveRows(self) -> list[dict[str, object]]:
        return self._preventive_rows

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
    def setRequestQueue(self, request_queue: str) -> None:
        apply_request_queue(self, request_queue)

    @Slot(str)
    def setWorkOrderQueue(self, work_order_queue: str) -> None:
        apply_work_order_queue(self, work_order_queue)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        apply_search_text(self, search_text)

    # --- Domain event wiring ---

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="maintenance_management")
        self._subscribe_domain_change("site", scope_code="platform")


__all__ = ["MaintenancePlannerWorkspaceController"]
