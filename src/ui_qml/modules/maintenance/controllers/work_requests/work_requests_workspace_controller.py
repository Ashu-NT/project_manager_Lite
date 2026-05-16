from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot

from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
    run_mutation,
    serialize_work_request_workspace_state,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenanceWorkRequestsWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)


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
            state = serialize_work_request_workspace_state(
                self._work_requests_workspace_presenter.build_workspace_state(
                    search_text=self._search_text,
                    site_filter=self._selected_site_filter,
                    status_filter=self._selected_status_filter,
                    priority_filter=self._selected_priority_filter,
                    asset_filter=self._selected_asset_filter,
                    selected_work_request_id=self._selected_work_request_id or None,
                )
            )
            self._set_overview(state["overview"])
            self._set_site_options(state["siteOptions"])
            self._set_status_options(state["statusOptions"])
            self._set_priority_options(state["priorityOptions"])
            self._set_asset_options(state["assetOptions"])
            self._set_selected_site_filter(str(state["selectedSiteFilter"]))
            self._set_selected_status_filter(str(state["selectedStatusFilter"]))
            self._set_selected_priority_filter(str(state["selectedPriorityFilter"]))
            self._set_selected_asset_filter(str(state["selectedAssetFilter"]))
            self._set_search_text(str(state["searchText"]))
            self._set_work_requests(state["workRequests"])
            self._set_selected_work_request_id(str(state["selectedWorkRequestId"]))
            self._set_selected_work_request(state["selectedWorkRequest"])
            self._set_form_site_options(state["formSiteOptions"])
            self._set_form_location_options(state["formLocationOptions"])
            self._set_form_system_options(state["formSystemOptions"])
            self._set_form_asset_options(state["formAssetOptions"])
            self._set_form_component_options(state["formComponentOptions"])
            self._set_form_source_type_options(state["formSourceTypeOptions"])
            self._set_form_priority_options(state["formPriorityOptions"])
            self._set_form_status_options(state["formStatusOptions"])
            self._set_empty_state(str(state["emptyState"]))
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized = (search_text or "").strip()
        if normalized == self._search_text:
            return
        self._set_search_text(normalized)
        self.refresh()

    @Slot(str)
    def setSiteFilter(self, site_id: str) -> None:
        normalized = (site_id or "").strip() or "all"
        if normalized == self._selected_site_filter:
            return
        self._set_selected_site_filter(normalized)
        self.refresh()

    @Slot(str)
    def setStatusFilter(self, status: str) -> None:
        normalized = (status or "").strip() or "all"
        if normalized == self._selected_status_filter:
            return
        self._set_selected_status_filter(normalized)
        self.refresh()

    @Slot(str)
    def setPriorityFilter(self, priority: str) -> None:
        normalized = (priority or "").strip() or "all"
        if normalized == self._selected_priority_filter:
            return
        self._set_selected_priority_filter(normalized)
        self.refresh()

    @Slot(str)
    def setAssetFilter(self, asset_id: str) -> None:
        normalized = (asset_id or "").strip() or "all"
        if normalized == self._selected_asset_filter:
            return
        self._set_selected_asset_filter(normalized)
        self.refresh()

    @Slot(str)
    def selectWorkRequest(self, work_request_id: str) -> None:
        normalized = (work_request_id or "").strip()
        if normalized == self._selected_work_request_id:
            return
        self._set_selected_work_request_id(normalized)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createWorkRequest(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._work_requests_workspace_presenter.create_work_request(
                dict(payload)
            ),
            success_message="Work request created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateWorkRequest(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._work_requests_workspace_presenter.update_work_request(
                dict(payload)
            ),
            success_message="Work request updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, str, int, result="QVariantMap")
    def setWorkRequestStatus(
        self,
        work_request_id: str,
        status: str,
        expected_version: int,
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._work_requests_workspace_presenter.set_work_request_status(
                work_request_id,
                status=status,
                expected_version=expected_version,
            ),
            success_message="Work request status updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="maintenance_management")
        self._subscribe_domain_change("site", scope_code="platform")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_site_options(self, options: list[dict[str, str]]) -> None:
        if options == self._site_options:
            return
        self._site_options = options
        self.siteOptionsChanged.emit()

    def _set_status_options(self, options: list[dict[str, str]]) -> None:
        if options == self._status_options:
            return
        self._status_options = options
        self.statusOptionsChanged.emit()

    def _set_priority_options(self, options: list[dict[str, str]]) -> None:
        if options == self._priority_options:
            return
        self._priority_options = options
        self.priorityOptionsChanged.emit()

    def _set_asset_options(self, options: list[dict[str, str]]) -> None:
        if options == self._asset_options:
            return
        self._asset_options = options
        self.assetOptionsChanged.emit()

    def _set_selected_site_filter(self, value: str) -> None:
        if value == self._selected_site_filter:
            return
        self._selected_site_filter = value
        self.selectedSiteFilterChanged.emit()

    def _set_selected_status_filter(self, value: str) -> None:
        if value == self._selected_status_filter:
            return
        self._selected_status_filter = value
        self.selectedStatusFilterChanged.emit()

    def _set_selected_priority_filter(self, value: str) -> None:
        if value == self._selected_priority_filter:
            return
        self._selected_priority_filter = value
        self.selectedPriorityFilterChanged.emit()

    def _set_selected_asset_filter(self, value: str) -> None:
        if value == self._selected_asset_filter:
            return
        self._selected_asset_filter = value
        self.selectedAssetFilterChanged.emit()

    def _set_search_text(self, value: str) -> None:
        if value == self._search_text:
            return
        self._search_text = value
        self.searchTextChanged.emit()

    def _set_work_requests(self, value: dict[str, object]) -> None:
        if value == self._work_requests:
            return
        self._work_requests = value
        self.workRequestsChanged.emit()

    def _set_selected_work_request(self, value: dict[str, object]) -> None:
        if value == self._selected_work_request:
            return
        self._selected_work_request = value
        self.selectedWorkRequestChanged.emit()

    def _set_selected_work_request_id(self, value: str) -> None:
        if value == self._selected_work_request_id:
            return
        self._selected_work_request_id = value
        self.selectedWorkRequestIdChanged.emit()

    def _set_form_site_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_site_options:
            return
        self._form_site_options = value
        self.formSiteOptionsChanged.emit()

    def _set_form_location_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_location_options:
            return
        self._form_location_options = value
        self.formLocationOptionsChanged.emit()

    def _set_form_system_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_system_options:
            return
        self._form_system_options = value
        self.formSystemOptionsChanged.emit()

    def _set_form_asset_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_asset_options:
            return
        self._form_asset_options = value
        self.formAssetOptionsChanged.emit()

    def _set_form_component_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_component_options:
            return
        self._form_component_options = value
        self.formComponentOptionsChanged.emit()

    def _set_form_source_type_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_source_type_options:
            return
        self._form_source_type_options = value
        self.formSourceTypeOptionsChanged.emit()

    def _set_form_priority_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_priority_options:
            return
        self._form_priority_options = value
        self.formPriorityOptionsChanged.emit()

    def _set_form_status_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_status_options:
            return
        self._form_status_options = value
        self.formStatusOptionsChanged.emit()


__all__ = ["MaintenanceWorkRequestsWorkspaceController"]
