from __future__ import annotations

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

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

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
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
    resourcePageChanged = Signal()
    resourcePageSizeChanged = Signal()
    resourceTotalCountChanged = Signal()
    selectedResourceIdsChanged = Signal()
    selectedResourceCountChanged = Signal()

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
        self._resource_page = 1
        self._resource_page_size = 25
        self._resource_total_count = 0
        self._selected_resource_ids: list[str] = []
        self._selected_resource_count = 0
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

    @Property(int, notify=resourcePageChanged)
    def resourcePage(self) -> int:
        return self._resource_page

    @Property(int, notify=resourcePageSizeChanged)
    def resourcePageSize(self) -> int:
        return self._resource_page_size

    @Property(int, notify=resourceTotalCountChanged)
    def resourceTotalCount(self) -> int:
        return self._resource_total_count

    @Property("QVariantList", notify=selectedResourceIdsChanged)
    def selectedResourceIds(self) -> list[str]:
        return list(self._selected_resource_ids)

    @Property(int, notify=selectedResourceCountChanged)
    def selectedResourceCount(self) -> int:
        return self._selected_resource_count

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
                page=self._resource_page,
                page_size=self._resource_page_size,
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
            self._set_resource_total_count(workspace_state.total_count)
            self._set_resource_page(workspace_state.page)
            self._set_resource_page_size(workspace_state.page_size)
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
        self._resource_page = 1
        self.refresh()

    @Slot(str)
    def setActiveFilter(self, active_filter: str) -> None:
        normalized_value = (active_filter or "").strip().lower() or "all"
        if normalized_value == self._selected_active_filter:
            return
        self._set_selected_active_filter(normalized_value)
        self._resource_page = 1
        self.refresh()

    @Slot(str)
    def setCategoryFilter(self, category_filter: str) -> None:
        normalized_value = (category_filter or "").strip().upper() or "ALL"
        if normalized_value == self._selected_category_filter.upper():
            return
        self._set_selected_category_filter(category_filter)
        self._resource_page = 1
        self.refresh()

    @Slot(str)
    def selectResource(self, resource_id: str) -> None:
        normalized_value = (resource_id or "").strip()
        if normalized_value == self._selected_resource_id:
            return
        self._set_selected_resource_id(normalized_value)

    @Slot(str)
    def activateResource(self, resource_id: str) -> None:
        self.selectResource(resource_id)
        QTimer.singleShot(0, self.refresh)

    @Slot(int)
    def setResourcePage(self, page: int) -> None:
        p = max(1, page)
        if p == self._resource_page:
            return
        self._set_resource_page(p)
        self.refresh()

    @Slot(int)
    def setResourcePageSize(self, page_size: int) -> None:
        if page_size <= 0 or page_size == self._resource_page_size:
            return
        self._resource_page_size = page_size
        self.resourcePageSizeChanged.emit()
        self._set_resource_page(1)
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

    @Slot(str, bool)
    def setResourceBulkSelection(self, resource_id: str, selected: bool) -> None:
        normalized_id = (resource_id or "").strip()
        if not normalized_id:
            return
        current = list(self._selected_resource_ids)
        if selected and normalized_id not in current:
            current.append(normalized_id)
        elif not selected and normalized_id in current:
            current.remove(normalized_id)
        else:
            return
        self._set_selected_resource_ids(current)

    @Slot()
    def clearResourceBulkSelection(self) -> None:
        self._set_selected_resource_ids([])

    @Slot()
    def selectVisibleResources(self) -> None:
        items = self._resources.get("items") or []
        visible_ids = [
            str(item.get("id", "") or "")
            for item in items
            if item.get("id")
        ]
        self._set_selected_resource_ids(visible_ids)

    @Slot("QVariantList", result="QVariantMap")
    def bulkDeleteResources(self, resource_ids: list) -> dict[str, object]:
        ids = [str(rid) for rid in (resource_ids or []) if rid]
        if not ids:
            return {}
        return run_mutation(
            operation=lambda: self._do_bulk_delete(ids),
            success_message=f"{len(ids)} resource(s) deleted.",
            on_success=self._on_bulk_mutation_success,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot()
    def exportResources(self) -> None:
        self._set_error_message("")
        self._set_feedback_message(
            "Resource export is not implemented yet in the QML workspace."
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

    def _set_resource_page(self, v: int) -> None:
        if v == self._resource_page:
            return
        self._resource_page = v
        self.resourcePageChanged.emit()

    def _set_resource_page_size(self, v: int) -> None:
        if v == self._resource_page_size:
            return
        self._resource_page_size = v
        self.resourcePageSizeChanged.emit()

    def _set_resource_total_count(self, v: int) -> None:
        if v == self._resource_total_count:
            return
        self._resource_total_count = v
        self.resourceTotalCountChanged.emit()

    def _set_selected_resource_ids(self, selected_ids: list[str]) -> None:
        if selected_ids == self._selected_resource_ids:
            return
        self._selected_resource_ids = selected_ids
        count = len(selected_ids)
        self.selectedResourceIdsChanged.emit()
        if count != self._selected_resource_count:
            self._selected_resource_count = count
            self.selectedResourceCountChanged.emit()

    def _on_bulk_mutation_success(self) -> None:
        self._set_selected_resource_ids([])
        self.refresh()

    def _do_bulk_delete(self, ids: list[str]) -> None:
        for resource_id in ids:
            self._resources_workspace_presenter.delete_resource(resource_id)


__all__ = ["ProjectManagementResourcesWorkspaceController"]
