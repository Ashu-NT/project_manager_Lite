from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot

from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
    serialize_planner_workspace_state,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenancePlannerWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)


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
            state = serialize_planner_workspace_state(
                self._planner_workspace_presenter.build_workspace_state(
                    site_id=self._normalized_filter(self._selected_site_filter),
                    asset_id=self._normalized_filter(self._selected_asset_filter),
                    system_id=self._normalized_filter(self._selected_system_filter),
                    request_queue=self._selected_request_queue,
                    work_order_queue=self._selected_work_order_queue,
                    search_text=self._search_text,
                )
            )
            self._set_overview(state["overview"])
            self._set_site_options(state["siteOptions"])
            self._set_asset_options(state["assetOptions"])
            self._set_system_options(state["systemOptions"])
            self._set_request_queue_options(state["requestQueueOptions"])
            self._set_work_order_queue_options(state["workOrderQueueOptions"])
            self._set_selected_site_filter(str(state["selectedSiteFilter"]))
            self._set_selected_asset_filter(str(state["selectedAssetFilter"]))
            self._set_selected_system_filter(str(state["selectedSystemFilter"]))
            self._set_selected_request_queue(str(state["selectedRequestQueue"]))
            self._set_selected_work_order_queue(str(state["selectedWorkOrderQueue"]))
            self._set_search_text(str(state["searchText"]))
            self._set_request_rows(state["requestRows"])
            self._set_work_order_rows(state["workOrderRows"])
            self._set_material_rows(state["materialRows"])
            self._set_preventive_rows(state["preventiveRows"])
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
    def setRequestQueue(self, request_queue: str) -> None:
        self._set_selected_request_queue(request_queue)
        self.refresh()

    @Slot(str)
    def setWorkOrderQueue(self, work_order_queue: str) -> None:
        self._set_selected_work_order_queue(work_order_queue)
        self.refresh()

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized = str(search_text or "").strip()
        if normalized == self._search_text:
            return
        self._set_search_text(normalized)
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

    def _set_request_queue_options(self, options: list[dict[str, object]]) -> None:
        if options == self._request_queue_options:
            return
        self._request_queue_options = options
        self.requestQueueOptionsChanged.emit()

    def _set_work_order_queue_options(
        self,
        options: list[dict[str, object]],
    ) -> None:
        if options == self._work_order_queue_options:
            return
        self._work_order_queue_options = options
        self.workOrderQueueOptionsChanged.emit()

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

    def _set_selected_request_queue(self, value: str) -> None:
        if value == self._selected_request_queue:
            return
        self._selected_request_queue = value
        self.selectedRequestQueueChanged.emit()

    def _set_selected_work_order_queue(self, value: str) -> None:
        if value == self._selected_work_order_queue:
            return
        self._selected_work_order_queue = value
        self.selectedWorkOrderQueueChanged.emit()

    def _set_search_text(self, value: str) -> None:
        if value == self._search_text:
            return
        self._search_text = value
        self.searchTextChanged.emit()

    def _set_request_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._request_rows:
            return
        self._request_rows = rows
        self.requestRowsChanged.emit()

    def _set_work_order_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._work_order_rows:
            return
        self._work_order_rows = rows
        self.workOrderRowsChanged.emit()

    def _set_material_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._material_rows:
            return
        self._material_rows = rows
        self.materialRowsChanged.emit()

    def _set_preventive_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._preventive_rows:
            return
        self._preventive_rows = rows
        self.preventiveRowsChanged.emit()

    def _set_recurring_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._recurring_rows:
            return
        self._recurring_rows = rows
        self.recurringRowsChanged.emit()

    @staticmethod
    def _normalized_filter(value: str) -> str | None:
        normalized = str(value or "").strip()
        return "" if normalized in {"", "all"} else normalized


__all__ = ["MaintenancePlannerWorkspaceController"]
