from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenanceWorkOrdersWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)
from .work_orders_mutations import (
    create_work_order,
    set_work_order_status,
    update_work_order,
)
from .work_orders_selection import (
    apply_asset_filter,
    apply_priority_filter,
    apply_search_text,
    apply_select_work_order,
    apply_site_filter,
    apply_status_filter,
    apply_work_order_type_filter,
)
from .work_orders_state_loader import load_workspace_state

QML_IMPORT_NAME = "Maintenance.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Maintenance workspace controllers are provided by the shell runtime.")
class MaintenanceWorkOrdersWorkspaceController(MaintenanceWorkspaceControllerBase):
    overviewChanged = Signal()
    siteOptionsChanged = Signal()
    statusOptionsChanged = Signal()
    priorityOptionsChanged = Signal()
    workOrderTypeOptionsChanged = Signal()
    assetOptionsChanged = Signal()
    selectedSiteFilterChanged = Signal()
    selectedStatusFilterChanged = Signal()
    selectedPriorityFilterChanged = Signal()
    selectedWorkOrderTypeFilterChanged = Signal()
    selectedAssetFilterChanged = Signal()
    searchTextChanged = Signal()
    workOrdersChanged = Signal()
    selectedWorkOrderChanged = Signal()
    selectedWorkOrderIdChanged = Signal()
    formSiteOptionsChanged = Signal()
    formLocationOptionsChanged = Signal()
    formSystemOptionsChanged = Signal()
    formAssetOptionsChanged = Signal()
    formComponentOptionsChanged = Signal()
    formSourceTypeOptionsChanged = Signal()
    formSourceWorkRequestOptionsChanged = Signal()
    formWorkOrderTypeOptionsChanged = Signal()
    formPriorityOptionsChanged = Signal()
    formStatusOptionsChanged = Signal()
    formEmployeeOptionsChanged = Signal()
    formVendorOptionsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: MaintenanceWorkspacePresenter | None = None,
        work_orders_workspace_presenter: MaintenanceWorkOrdersWorkspacePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or MaintenanceWorkspacePresenter(
            "maintenance_management.work_orders"
        )
        self._work_orders_workspace_presenter = (
            work_orders_workspace_presenter
            or MaintenanceWorkOrdersWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._site_options: list[dict[str, object]] = []
        self._status_options: list[dict[str, object]] = []
        self._priority_options: list[dict[str, object]] = []
        self._work_order_type_options: list[dict[str, object]] = []
        self._asset_options: list[dict[str, object]] = []
        self._selected_site_filter = "all"
        self._selected_status_filter = "all"
        self._selected_priority_filter = "all"
        self._selected_work_order_type_filter = "all"
        self._selected_asset_filter = "all"
        self._search_text = ""
        self._work_orders_table_model = DynamicTableModel(self)
        self._work_orders: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_work_order: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._selected_work_order_id = ""
        self._form_site_options: list[dict[str, str]] = []
        self._form_location_options: list[dict[str, str]] = []
        self._form_system_options: list[dict[str, str]] = []
        self._form_asset_options: list[dict[str, str]] = []
        self._form_component_options: list[dict[str, str]] = []
        self._form_source_type_options: list[dict[str, str]] = []
        self._form_source_work_request_options: list[dict[str, object]] = []
        self._form_work_order_type_options: list[dict[str, str]] = []
        self._form_priority_options: list[dict[str, str]] = []
        self._form_status_options: list[dict[str, str]] = []
        self._form_employee_options: list[dict[str, str]] = []
        self._form_vendor_options: list[dict[str, str]] = []
        self._bind_domain_events()
        self.refresh()

    # --- Qt Properties ---

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=siteOptionsChanged)
    def siteOptions(self) -> list[dict[str, object]]:
        return self._site_options

    @Property("QVariantList", notify=statusOptionsChanged)
    def statusOptions(self) -> list[dict[str, object]]:
        return self._status_options

    @Property("QVariantList", notify=priorityOptionsChanged)
    def priorityOptions(self) -> list[dict[str, object]]:
        return self._priority_options

    @Property("QVariantList", notify=workOrderTypeOptionsChanged)
    def workOrderTypeOptions(self) -> list[dict[str, object]]:
        return self._work_order_type_options

    @Property("QVariantList", notify=assetOptionsChanged)
    def assetOptions(self) -> list[dict[str, object]]:
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

    @Property(str, notify=selectedWorkOrderTypeFilterChanged)
    def selectedWorkOrderTypeFilter(self) -> str:
        return self._selected_work_order_type_filter

    @Property(str, notify=selectedAssetFilterChanged)
    def selectedAssetFilter(self) -> str:
        return self._selected_asset_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=workOrdersChanged)
    def workOrders(self) -> dict[str, object]:
        return self._work_orders

    @Property(QObject, constant=True)
    def workOrdersTableModel(self) -> DynamicTableModel:
        return self._work_orders_table_model

    @Property("QVariantMap", notify=selectedWorkOrderChanged)
    def selectedWorkOrder(self) -> dict[str, object]:
        return self._selected_work_order

    @Property(str, notify=selectedWorkOrderIdChanged)
    def selectedWorkOrderId(self) -> str:
        return self._selected_work_order_id

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

    @Property("QVariantList", notify=formSourceWorkRequestOptionsChanged)
    def formSourceWorkRequestOptions(self) -> list[dict[str, object]]:
        return self._form_source_work_request_options

    @Property("QVariantList", notify=formWorkOrderTypeOptionsChanged)
    def formWorkOrderTypeOptions(self) -> list[dict[str, str]]:
        return self._form_work_order_type_options

    @Property("QVariantList", notify=formPriorityOptionsChanged)
    def formPriorityOptions(self) -> list[dict[str, str]]:
        return self._form_priority_options

    @Property("QVariantList", notify=formStatusOptionsChanged)
    def formStatusOptions(self) -> list[dict[str, str]]:
        return self._form_status_options

    @Property("QVariantList", notify=formEmployeeOptionsChanged)
    def formEmployeeOptions(self) -> list[dict[str, str]]:
        return self._form_employee_options

    @Property("QVariantList", notify=formVendorOptionsChanged)
    def formVendorOptions(self) -> list[dict[str, str]]:
        return self._form_vendor_options

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
    def setWorkOrderTypeFilter(self, work_order_type: str) -> None:
        apply_work_order_type_filter(self, work_order_type)

    @Slot(str)
    def setAssetFilter(self, asset_id: str) -> None:
        apply_asset_filter(self, asset_id)

    @Slot(str)
    def selectWorkOrder(self, work_order_id: str) -> None:
        apply_select_work_order(self, work_order_id)

    @Slot("QVariantMap", result="QVariantMap")
    def createWorkOrder(self, payload: dict[str, object]) -> dict[str, object]:
        return create_work_order(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateWorkOrder(self, payload: dict[str, object]) -> dict[str, object]:
        return update_work_order(self, payload)

    @Slot(str, str, int, result="QVariantMap")
    def setWorkOrderStatus(
        self, work_order_id: str, status: str, expected_version: int
    ) -> dict[str, object]:
        return set_work_order_status(self, work_order_id, status, expected_version)

    # --- Domain event wiring ---

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="maintenance_management")
        self._subscribe_domain_change("site", scope_code="platform")


__all__ = ["MaintenanceWorkOrdersWorkspaceController"]
