from __future__ import annotations


class ResourceStateSettersMixin:

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
        self._table_models.resources.set_rows(resources.get("items", []))
        self.resourcesChanged.emit()

    def _set_selected_resource(self, selected_resource: dict[str, object]) -> None:
        if selected_resource == self._selected_resource:
            return
        self._selected_resource = selected_resource
        self.selectedResourceChanged.emit()

    def _set_resource_inspector(self, inspector: dict[str, object]) -> None:
        if inspector == self._resource_inspector:
            return
        self._resource_inspector = inspector
        self.resourceInspectorChanged.emit()

    def _set_inspector_loading(self, value: bool) -> None:
        if value == self._inspector_loading:
            return
        self._inspector_loading = value
        self.inspectorLoadingChanged.emit()

    def _set_inspector_error(self, value: str) -> None:
        if value == self._inspector_error:
            return
        self._inspector_error = value
        self.inspectorErrorChanged.emit()

    def _set_detail_loading(self, value: bool) -> None:
        if value == self._detail_loading:
            return
        self._detail_loading = value
        self.detailLoadingChanged.emit()

    def _set_detail_error(self, value: str) -> None:
        if value == self._detail_error:
            return
        self._detail_error = value
        self.detailErrorChanged.emit()

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

    def _set_resource_sort_key(self, value: str) -> None:
        if value == self._resource_sort_key:
            return
        self._resource_sort_key = value
        self.resourceSortKeyChanged.emit()

    def _set_resource_sort_direction(self, value: int) -> None:
        if value == self._resource_sort_direction:
            return
        self._resource_sort_direction = value
        self.resourceSortDirectionChanged.emit()

    def _set_selected_resource_ids(self, selected_ids: list[str]) -> None:
        if selected_ids == self._selected_resource_ids:
            return
        self._selected_resource_ids = selected_ids
        count = len(selected_ids)
        self.selectedResourceIdsChanged.emit()
        if count != self._selected_resource_count:
            self._selected_resource_count = count
            self.selectedResourceCountChanged.emit()

    def _set_resource_availability(self, availability: dict[str, object]) -> None:
        if availability == self._resource_availability:
            return
        self._resource_availability = availability
        self.resourceAvailabilityChanged.emit()


__all__ = ["ResourceStateSettersMixin"]
