from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenanceWorkRequestsWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)
from .work_requests_mutations import (
    create_work_request,
    set_work_request_status,
    update_work_request,
)
from .work_requests_selection import (
    apply_asset_filter,
    apply_priority_filter,
    apply_search_text,
    apply_select_work_request,
    apply_site_filter,
    apply_status_filter,
)
from .work_requests_state_loader import load_workspace_state

QML_IMPORT_NAME = "Maintenance.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Maintenance workspace controllers are provided by the shell runtime.")
class MaintenanceWorkRequestsWorkspaceController(MaintenanceWorkspaceControllerBase):
    overviewChanged = Signal()
    siteOptionsChanged = Signal()
    statusOptionsChanged = Signal()
    priorityOptionsChanged = Signal()
    assetOptionsChanged = Signal()
    selectedSiteFilterChanged = Signal()
    selectedStatusFilterChanged = Signal()
    selectedPriorityFilterChanged = Signal()
    selectedAssetFilterChanged = Signal()
    searchTextChanged = Signal()
    workRequestsChanged = Signal()
    selectedWorkRequestChanged = Signal()
    selectedWorkRequestIdChanged = Signal()
    formSiteOptionsChanged = Signal()
    formLocationOptionsChanged = Signal()
    formSystemOptionsChanged = Signal()
    formAssetOptionsChanged = Signal()
    formComponentOptionsChanged = Signal()
    formSourceTypeOptionsChanged = Signal()
    formPriorityOptionsChanged = Signal()
    formStatusOptionsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: MaintenanceWorkspacePresenter | None = None,
        work_requests_workspace_presenter: MaintenanceWorkRequestsWorkspacePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or MaintenanceWorkspacePresenter(
            "maintenance_management.work_requests"
        )
        self._work_requests_workspace_presenter = (
            work_requests_workspace_presenter
            or MaintenanceWorkRequestsWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._site_options: list[dict[str, str]] = []
        self._status_options: list[dict[str, str]] = []
        self._priority_options: list[dict[str, str]] = []
        self._asset_options: list[dict[str, str]] = []
        self._selected_site_filter = "all"
        self._selected_status_filter = "all"
        self._selected_priority_filter = "all"
        self._selected_asset_filter = "all"
        self._search_text = ""
        self._work_requests_table_model = DynamicTableModel(self)
        self._work_requests: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_work_request: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._selected_work_request_id = ""
        self._form_site_options: list[dict[str, str]] = []
        self._form_location_options: list[dict[str, str]] = []
        self._form_system_options: list[dict[str, str]] = []
        self._form_asset_options: list[dict[str, str]] = []
        self._form_component_options: list[dict[str, str]] = []
        self._form_source_type_options: list[dict[str, str]] = []
        self._form_priority_options: list[dict[str, str]] = []
        self._form_status_options: list[dict[str, str]] = []
        self._bind_domain_events()
        self.refresh()

    # --- Qt Properties ---

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=siteOptionsChanged)
    def siteOptions(self) -> list[dict[str, str]]:
        return self._site_options

    @Property("QVariantList", notify=statusOptionsChanged)
    def statusOptions(self) -> list[dict[str, str]]:
        return self._status_options

    @Property("QVariantList", notify=priorityOptionsChanged)
    def priorityOptions(self) -> list[dict[str, str]]:
        return self._priority_options

    @Property("QVariantList", notify=assetOptionsChanged)
    def assetOptions(self) -> list[dict[str, str]]:
        return self._asset_options

    @Property(str, notify=selectedSiteFilterChanged)
    def selectedSiteFilter(self) -> str:
        return self._selected_site_filter

    @Property(str, notify=selectedStatusFilterChanged)
    def selectedStatusFilter(self) -> str:
        return self._selected_status_filter

    @Property(str, notify=selectedPriorityFilterChanged)
    def selectedPriorityFilter(self) -> str:
        return self._selected_priority_filter

    @Property(str, notify=selectedAssetFilterChanged)
    def selectedAssetFilter(self) -> str:
        return self._selected_asset_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=workRequestsChanged)
    def workRequests(self) -> dict[str, object]:
        return self._work_requests

    @Property(QObject, constant=True)
    def workRequestsTableModel(self) -> DynamicTableModel:
        return self._work_requests_table_model

    @Property("QVariantMap", notify=selectedWorkRequestChanged)
    def selectedWorkRequest(self) -> dict[str, object]:
        return self._selected_work_request

    @Property(str, notify=selectedWorkRequestIdChanged)
    def selectedWorkRequestId(self) -> str:
        return self._selected_work_request_id

    @Property("QVariantList", notify=formSiteOptionsChanged)
    def formSiteOptions(self) -> list[dict[str, str]]:
        return self._form_site_options

    @Property("QVariantList", notify=formLocationOptionsChanged)
    def formLocationOptions(self) -> list[dict[str, str]]:
        return self._form_location_options

    @Property("QVariantList", notify=formSystemOptionsChanged)
    def formSystemOptions(self) -> list[dict[str, str]]:
        return self._form_system_options

    @Property("QVariantList", notify=formAssetOptionsChanged)
    def formAssetOptions(self) -> list[dict[str, str]]:
        return self._form_asset_options

    @Property("QVariantList", notify=formComponentOptionsChanged)
    def formComponentOptions(self) -> list[dict[str, str]]:
        return self._form_component_options

    @Property("QVariantList", notify=formSourceTypeOptionsChanged)
    def formSourceTypeOptions(self) -> list[dict[str, str]]:
        return self._form_source_type_options

    @Property("QVariantList", notify=formPriorityOptionsChanged)
    def formPriorityOptions(self) -> list[dict[str, str]]:
        return self._form_priority_options

    @Property("QVariantList", notify=formStatusOptionsChanged)
    def formStatusOptions(self) -> list[dict[str, str]]:
        return self._form_status_options

    # --- Slots ---

    @Slot()
    def refresh(self) -> None:
        load_workspace_state(self)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        apply_search_text(self, search_text)

    @Slot(str)
    def setSiteFilter(self, site_id: str) -> None:
        apply_site_filter(self, site_id)

    @Slot(str)
    def setStatusFilter(self, status: str) -> None:
        apply_status_filter(self, status)

    @Slot(str)
    def setPriorityFilter(self, priority: str) -> None:
        apply_priority_filter(self, priority)

    @Slot(str)
    def setAssetFilter(self, asset_id: str) -> None:
        apply_asset_filter(self, asset_id)

    @Slot(str)
    def selectWorkRequest(self, work_request_id: str) -> None:
        apply_select_work_request(self, work_request_id)

    @Slot("QVariantMap", result="QVariantMap")
    def createWorkRequest(self, payload: dict[str, object]) -> dict[str, object]:
        return create_work_request(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateWorkRequest(self, payload: dict[str, object]) -> dict[str, object]:
        return update_work_request(self, payload)

    @Slot(str, str, int, result="QVariantMap")
    def setWorkRequestStatus(
        self,
        work_request_id: str,
        status: str,
        expected_version: int,
    ) -> dict[str, object]:
        return set_work_request_status(self, work_request_id, status, expected_version)

    # --- Domain event wiring ---

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="maintenance_management")
        self._subscribe_domain_change("site", scope_code="platform")


__all__ = ["MaintenanceWorkRequestsWorkspaceController"]
