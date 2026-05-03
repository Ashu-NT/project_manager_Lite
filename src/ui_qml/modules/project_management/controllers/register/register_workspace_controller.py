from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_register_collection_view_model,
    serialize_register_detail_view_model,
    serialize_register_overview_view_model,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectRegisterWorkspacePresenter,
)


class ProjectManagementRegisterWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    typeOptionsChanged = Signal()
    statusOptionsChanged = Signal()
    severityOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    selectedTypeFilterChanged = Signal()
    selectedStatusFilterChanged = Signal()
    selectedSeverityFilterChanged = Signal()
    searchTextChanged = Signal()
    entriesChanged = Signal()
    selectedEntryChanged = Signal()
    selectedEntryIdChanged = Signal()
    urgentEntriesChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        register_workspace_presenter: ProjectRegisterWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.register"
        )
        self._register_workspace_presenter = (
            register_workspace_presenter or ProjectRegisterWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._project_options: list[dict[str, str]] = []
        self._type_options: list[dict[str, str]] = []
        self._status_options: list[dict[str, str]] = []
        self._severity_options: list[dict[str, str]] = []
        self._selected_project_id = "all"
        self._selected_type_filter = "all"
        self._selected_status_filter = "all"
        self._selected_severity_filter = "all"
        self._search_text = ""
        self._entries: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_entry: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._selected_entry_id = ""
        self._urgent_entries: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> list[dict[str, str]]:
        return self._project_options

    @Property("QVariantList", notify=typeOptionsChanged)
    def typeOptions(self) -> list[dict[str, str]]:
        return self._type_options

    @Property("QVariantList", notify=statusOptionsChanged)
    def statusOptions(self) -> list[dict[str, str]]:
        return self._status_options

    @Property("QVariantList", notify=severityOptionsChanged)
    def severityOptions(self) -> list[dict[str, str]]:
        return self._severity_options

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str:
        return self._selected_project_id

    @Property(str, notify=selectedTypeFilterChanged)
    def selectedTypeFilter(self) -> str:
        return self._selected_type_filter

    @Property(str, notify=selectedStatusFilterChanged)
    def selectedStatusFilter(self) -> str:
        return self._selected_status_filter

    @Property(str, notify=selectedSeverityFilterChanged)
    def selectedSeverityFilter(self) -> str:
        return self._selected_severity_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=entriesChanged)
    def entries(self) -> dict[str, object]:
        return self._entries

    @Property("QVariantMap", notify=selectedEntryChanged)
    def selectedEntry(self) -> dict[str, object]:
        return self._selected_entry

    @Property(str, notify=selectedEntryIdChanged)
    def selectedEntryId(self) -> str:
        return self._selected_entry_id

    @Property("QVariantMap", notify=urgentEntriesChanged)
    def urgentEntries(self) -> dict[str, object]:
        return self._urgent_entries

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
            workspace_state = self._register_workspace_presenter.build_workspace_state(
                project_id=self._selected_project_id,
                type_filter=self._selected_type_filter,
                status_filter=self._selected_status_filter,
                severity_filter=self._selected_severity_filter,
                search_text=self._search_text,
                selected_entry_id=self._selected_entry_id or None,
            )
            self._set_overview(
                serialize_register_overview_view_model(workspace_state.overview)
            )
            self._set_project_options(
                serialize_selector_options(workspace_state.project_options)
            )
            self._set_type_options(
                serialize_selector_options(workspace_state.type_options)
            )
            self._set_status_options(
                serialize_selector_options(workspace_state.status_options)
            )
            self._set_severity_options(
                serialize_selector_options(workspace_state.severity_options)
            )
            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_selected_type_filter(workspace_state.selected_type_filter)
            self._set_selected_status_filter(workspace_state.selected_status_filter)
            self._set_selected_severity_filter(workspace_state.selected_severity_filter)
            self._set_search_text(workspace_state.search_text)
            self._set_entries(
                serialize_register_collection_view_model(workspace_state.entries)
            )
            self._set_selected_entry_id(workspace_state.selected_entry_id)
            self._set_selected_entry(
                serialize_register_detail_view_model(
                    workspace_state.selected_entry_detail
                )
            )
            self._set_urgent_entries(
                serialize_register_collection_view_model(
                    workspace_state.urgent_entries
                )
            )
            self._set_empty_state(workspace_state.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        normalized_value = (project_id or "").strip() or "all"
        if normalized_value == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_value)
        self.refresh()

    @Slot(str)
    def setTypeFilter(self, type_filter: str) -> None:
        normalized_value = (type_filter or "").strip() or "all"
        if normalized_value == self._selected_type_filter:
            return
        self._set_selected_type_filter(normalized_value)
        self.refresh()

    @Slot(str)
    def setStatusFilter(self, status_filter: str) -> None:
        normalized_value = (status_filter or "").strip() or "all"
        if normalized_value == self._selected_status_filter:
            return
        self._set_selected_status_filter(normalized_value)
        self.refresh()

    @Slot(str)
    def setSeverityFilter(self, severity_filter: str) -> None:
        normalized_value = (severity_filter or "").strip() or "all"
        if normalized_value == self._selected_severity_filter:
            return
        self._set_selected_severity_filter(normalized_value)
        self.refresh()

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized_value = (search_text or "").strip()
        if normalized_value == self._search_text:
            return
        self._set_search_text(normalized_value)
        self.refresh()

    @Slot(str)
    def selectEntry(self, entry_id: str) -> None:
        normalized_value = (entry_id or "").strip()
        if normalized_value == self._selected_entry_id:
            return
        self._set_selected_entry_id(normalized_value)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._register_workspace_presenter.create_entry(
                dict(payload)
            ),
            success_message="Register entry created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._register_workspace_presenter.update_entry(
                dict(payload)
            ),
            success_message="Register entry updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteEntry(self, entry_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._register_workspace_presenter.delete_entry(
                entry_id
            ),
            success_message="Register entry deleted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "register_scope",
            scope_code="project_management",
        )

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


__all__ = ["ProjectManagementRegisterWorkspaceController"]
