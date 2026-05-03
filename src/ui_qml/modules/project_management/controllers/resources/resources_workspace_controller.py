from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.core.platform.notifications.domain_events import domain_events
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_resource_catalog_overview_view_model,
    serialize_resource_detail_view_model,
    serialize_resource_employee_option_view_models,
    serialize_resource_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectResourcesWorkspacePresenter,
)


class ProjectManagementResourcesWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    workerTypeOptionsChanged = Signal()
    categoryOptionsChanged = Signal()
    employeeOptionsChanged = Signal()
    selectedActiveFilterChanged = Signal()
    selectedCategoryFilterChanged = Signal()
    searchTextChanged = Signal()
    resourcesChanged = Signal()
    selectedResourceChanged = Signal()
    selectedResourceIdChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        resources_workspace_presenter: ProjectResourcesWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.resources"
        )
        self._resources_workspace_presenter = (
            resources_workspace_presenter or ProjectResourcesWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._worker_type_options: list[dict[str, object]] = []
        self._category_options: list[dict[str, object]] = []
        self._employee_options: list[dict[str, object]] = []
        self._selected_active_filter = "all"
        self._selected_category_filter = "all"
        self._search_text = ""
        self._resources: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_resource: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._selected_resource_id = ""
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=workerTypeOptionsChanged)
    def workerTypeOptions(self) -> list[dict[str, object]]:
        return self._worker_type_options

    @Property("QVariantList", notify=categoryOptionsChanged)
    def categoryOptions(self) -> list[dict[str, object]]:
        return self._category_options

    @Property("QVariantList", notify=employeeOptionsChanged)
    def employeeOptions(self) -> list[dict[str, object]]:
        return self._employee_options

    @Property(str, notify=selectedActiveFilterChanged)
    def selectedActiveFilter(self) -> str:
        return self._selected_active_filter

    @Property(str, notify=selectedCategoryFilterChanged)
    def selectedCategoryFilter(self) -> str:
        return self._selected_category_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=resourcesChanged)
    def resources(self) -> dict[str, object]:
        return self._resources

    @Property("QVariantMap", notify=selectedResourceChanged)
    def selectedResource(self) -> dict[str, object]:
        return self._selected_resource

    @Property(str, notify=selectedResourceIdChanged)
    def selectedResourceId(self) -> str:
        return self._selected_resource_id

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
            workspace_state = self._resources_workspace_presenter.build_workspace_state(
                search_text=self._search_text,
                active_filter=self._selected_active_filter,
                category_filter=self._selected_category_filter,
                selected_resource_id=self._selected_resource_id or None,
            )
            self._set_overview(
                serialize_resource_catalog_overview_view_model(
                    workspace_state.overview
                )
            )
            self._set_worker_type_options(
                serialize_selector_options(workspace_state.worker_type_options)
            )
            self._set_category_options(
                serialize_selector_options(workspace_state.category_options)
            )
            self._set_employee_options(
                serialize_resource_employee_option_view_models(
                    workspace_state.employee_options
                )
            )
            self._set_selected_active_filter(workspace_state.selected_active_filter)
            self._set_selected_category_filter(workspace_state.selected_category_filter)
            self._set_search_text(workspace_state.search_text)
            self._set_resources(
                {
                    "title": "Resource Pool",
                    "subtitle": "Manage resource capacity, staffing type, and active availability.",
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_resource_record_view_models(
                        workspace_state.resources
                    ),
                }
            )
            self._set_selected_resource_id(workspace_state.selected_resource_id)
            self._set_selected_resource(
                serialize_resource_detail_view_model(
                    workspace_state.selected_resource_detail
                )
            )
            self._set_empty_state(workspace_state.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized_value = (search_text or "").strip()
        if normalized_value == self._search_text:
            return
        self._set_search_text(normalized_value)
        self.refresh()

    @Slot(str)
    def setActiveFilter(self, active_filter: str) -> None:
        normalized_value = (active_filter or "").strip().lower() or "all"
        if normalized_value == self._selected_active_filter:
            return
        self._set_selected_active_filter(normalized_value)
        self.refresh()

    @Slot(str)
    def setCategoryFilter(self, category_filter: str) -> None:
        normalized_value = (category_filter or "").strip().upper() or "ALL"
        if normalized_value == self._selected_category_filter.upper():
            return
        self._set_selected_category_filter(category_filter)
        self.refresh()

    @Slot(str)
    def selectResource(self, resource_id: str) -> None:
        normalized_value = (resource_id or "").strip()
        if normalized_value == self._selected_resource_id:
            return
        self._set_selected_resource_id(normalized_value)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createResource(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._resources_workspace_presenter.create_resource(
                dict(payload)
            ),
            success_message="Resource created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateResource(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._resources_workspace_presenter.update_resource(
                dict(payload)
            ),
            success_message="Resource updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, int, result="QVariantMap")
    def toggleResourceActive(
        self,
        resource_id: str,
        expected_version: int,
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._resources_workspace_presenter.toggle_resource_active(
                resource_id,
                expected_version=expected_version,
            ),
            success_message="Resource availability updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteResource(self, resource_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._resources_workspace_presenter.delete_resource(
                resource_id
            ),
            success_message="Resource deleted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change("resource", scope_code="project_management")
        self._subscribe_domain_signal(
            domain_events.employees_changed,
            self._on_domain_event,
        )

    def _on_domain_event(self, _payload: object) -> None:
        self._request_domain_refresh()

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_worker_type_options(self, worker_type_options: list[dict[str, object]]) -> None:
        if worker_type_options == self._worker_type_options:
            return
        self._worker_type_options = worker_type_options
        self.workerTypeOptionsChanged.emit()

    def _set_category_options(self, category_options: list[dict[str, object]]) -> None:
        if category_options == self._category_options:
            return
        self._category_options = category_options
        self.categoryOptionsChanged.emit()

    def _set_employee_options(self, employee_options: list[dict[str, object]]) -> None:
        if employee_options == self._employee_options:
            return
        self._employee_options = employee_options
        self.employeeOptionsChanged.emit()

    def _set_selected_active_filter(self, selected_active_filter: str) -> None:
        if selected_active_filter == self._selected_active_filter:
            return
        self._selected_active_filter = selected_active_filter
        self.selectedActiveFilterChanged.emit()

    def _set_selected_category_filter(self, selected_category_filter: str) -> None:
        if selected_category_filter == self._selected_category_filter:
            return
        self._selected_category_filter = selected_category_filter
        self.selectedCategoryFilterChanged.emit()

    def _set_search_text(self, search_text: str) -> None:
        if search_text == self._search_text:
            return
        self._search_text = search_text
        self.searchTextChanged.emit()

    def _set_resources(self, resources: dict[str, object]) -> None:
        if resources == self._resources:
            return
        self._resources = resources
        self.resourcesChanged.emit()

    def _set_selected_resource(self, selected_resource: dict[str, object]) -> None:
        if selected_resource == self._selected_resource:
            return
        self._selected_resource = selected_resource
        self.selectedResourceChanged.emit()

    def _set_selected_resource_id(self, selected_resource_id: str) -> None:
        if selected_resource_id == self._selected_resource_id:
            return
        self._selected_resource_id = selected_resource_id
        self.selectedResourceIdChanged.emit()


__all__ = ["ProjectManagementResourcesWorkspaceController"]
