from __future__ import annotations


class ProjectStateSettersMixin:

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_status_options(self, status_options: list[dict[str, str]]) -> None:
        if status_options == self._status_options:
            return
        self._status_options = status_options
        self.statusOptionsChanged.emit()

    def _set_selected_status_filter(self, selected_status_filter: str) -> None:
        if selected_status_filter == self._selected_status_filter:
            return
        self._selected_status_filter = selected_status_filter
        self.selectedStatusFilterChanged.emit()

    def _set_search_text(self, search_text: str) -> None:
        if search_text == self._search_text:
            return
        self._search_text = search_text
        self.searchTextChanged.emit()

    def _set_projects(self, projects: dict[str, object]) -> None:
        if projects == self._projects:
            return
        self._projects = projects
        self._table_models.projects.set_rows(projects.get("items", []))
        self.projectsChanged.emit()

    def _set_selected_project(self, selected_project: dict[str, object]) -> None:
        if selected_project == self._selected_project:
            return
        self._selected_project = selected_project
        self.selectedProjectChanged.emit()

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()

    def _set_project_page(self, v: int) -> None:
        if v == self._project_page:
            return
        self._project_page = v
        self.projectPageChanged.emit()

    def _set_project_page_size(self, v: int) -> None:
        if v == self._project_page_size:
            return
        self._project_page_size = v
        self.projectPageSizeChanged.emit()

    def _set_project_total_count(self, v: int) -> None:
        if v == self._project_total_count:
            return
        self._project_total_count = v
        self.projectTotalCountChanged.emit()

    def _set_selected_project_ids(self, selected_ids: list[str]) -> None:
        if selected_ids == self._selected_project_ids:
            return
        self._selected_project_ids = selected_ids
        count = len(selected_ids)
        self.selectedProjectIdsChanged.emit()
        if count != self._selected_project_count:
            self._selected_project_count = count
            self.selectedProjectCountChanged.emit()

    def _set_project_tasks(self, value: dict[str, object]) -> None:
        if value == self._project_tasks:
            return
        self._project_tasks = value
        self._table_models.project_tasks.set_rows(value.get("items", []))
        self.projectTasksChanged.emit()

    def _set_project_resources(self, value: dict[str, object]) -> None:
        if value == self._project_resources:
            return
        self._project_resources = value
        self._table_models.project_resources.set_rows(value.get("items", []))
        self.projectResourcesChanged.emit()

    def _set_project_financials(self, value: dict[str, object]) -> None:
        if value == self._project_financials:
            return
        self._project_financials = value
        self.projectFinancialsChanged.emit()

    def _set_project_risks(self, value: dict[str, object]) -> None:
        if value == self._project_risks:
            return
        self._project_risks = value
        self.projectRisksChanged.emit()

    def _set_project_documents(self, value: dict[str, object]) -> None:
        if value == self._project_documents:
            return
        self._project_documents = value
        self.projectDocumentsChanged.emit()

    def _set_project_activity(self, value: dict[str, object]) -> None:
        if value == self._project_activity:
            return
        self._project_activity = value
        self.projectActivityChanged.emit()

    def _set_import_preview(self, v: dict[str, object]) -> None:
        if v == self._import_preview:
            return
        self._import_preview = v
        self.importPreviewChanged.emit()

    def _set_import_busy(self, v: bool) -> None:
        if v == self._import_busy:
            return
        self._import_busy = v
        self.importBusyChanged.emit()

    def _set_import_error(self, v: str) -> None:
        if v == self._import_error:
            return
        self._import_error = v
        self.importErrorChanged.emit()

    def _set_assignable_resource_options(self, options: list[dict[str, str]]) -> None:
        if options == self._assignable_resource_options:
            return
        self._assignable_resource_options = options
        self.assignableResourceOptionsChanged.emit()


__all__ = ["ProjectStateSettersMixin"]
