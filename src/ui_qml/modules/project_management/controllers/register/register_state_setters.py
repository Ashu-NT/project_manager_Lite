from __future__ import annotations


class RegisterStateSettersMixin:

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_project_options(self, project_options: list[dict[str, str]]) -> None:
        if project_options == self._project_options:
            return
        self._project_options = project_options
        self.projectOptionsChanged.emit()

    def _set_type_options(self, type_options: list[dict[str, str]]) -> None:
        if type_options == self._type_options:
            return
        self._type_options = type_options
        self.typeOptionsChanged.emit()

    def _set_status_options(self, status_options: list[dict[str, str]]) -> None:
        if status_options == self._status_options:
            return
        self._status_options = status_options
        self.statusOptionsChanged.emit()

    def _set_severity_options(self, severity_options: list[dict[str, str]]) -> None:
        if severity_options == self._severity_options:
            return
        self._severity_options = severity_options
        self.severityOptionsChanged.emit()

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()

    def _set_selected_type_filter(self, selected_type_filter: str) -> None:
        if selected_type_filter == self._selected_type_filter:
            return
        self._selected_type_filter = selected_type_filter
        self.selectedTypeFilterChanged.emit()

    def _set_selected_status_filter(self, selected_status_filter: str) -> None:
        if selected_status_filter == self._selected_status_filter:
            return
        self._selected_status_filter = selected_status_filter
        self.selectedStatusFilterChanged.emit()

    def _set_selected_severity_filter(self, selected_severity_filter: str) -> None:
        if selected_severity_filter == self._selected_severity_filter:
            return
        self._selected_severity_filter = selected_severity_filter
        self.selectedSeverityFilterChanged.emit()

    def _set_search_text(self, search_text: str) -> None:
        if search_text == self._search_text:
            return
        self._search_text = search_text
        self.searchTextChanged.emit()

    def _set_entries(self, entries: dict[str, object]) -> None:
        if entries == self._entries:
            return
        self._entries = entries
        self._table_models.entries.set_rows(entries.get("items", []))
        self.entriesChanged.emit()

    def _set_selected_entry(self, selected_entry: dict[str, object]) -> None:
        if selected_entry == self._selected_entry:
            return
        self._selected_entry = selected_entry
        self.selectedEntryChanged.emit()

    def _set_selected_entry_id(self, selected_entry_id: str) -> None:
        if selected_entry_id == self._selected_entry_id:
            return
        self._selected_entry_id = selected_entry_id
        self.selectedEntryIdChanged.emit()

    def _set_urgent_entries(self, urgent_entries: dict[str, object]) -> None:
        if urgent_entries == self._urgent_entries:
            return
        self._urgent_entries = urgent_entries
        self.urgentEntriesChanged.emit()

    def _set_entry_page(self, v: int) -> None:
        if v == self._entry_page:
            return
        self._entry_page = v
        self.entryPageChanged.emit()

    def _set_entry_total_count(self, v: int) -> None:
        if v == self._entry_total_count:
            return
        self._entry_total_count = v
        self.entryTotalCountChanged.emit()

    def _set_selected_entry_ids(self, ids: list[str]) -> None:
        if ids == self._selected_entry_ids:
            return
        self._selected_entry_ids = ids
        self.selectedEntryIdsChanged.emit()
        self.selectedEntryCountChanged.emit()


__all__ = ["RegisterStateSettersMixin"]
