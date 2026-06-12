from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
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

from .register_state import (
    default_entries,
    default_overview,
    default_selected_entry,
    default_urgent_entries,
)
from .register_table_models import RegisterTableModels, create_register_table_models
from .register_state_setters import RegisterStateSettersMixin
from .register_domain_event_binder import bind_register_domain_events
from .register_selection_handler import (
    select_entry,
    select_project,
    set_entry_page,
    set_entry_page_size,
    set_search_text,
    set_severity_filter,
    set_status_filter,
    set_type_filter,
)
from .register_bulk_handler import (
    apply_bulk_entry_status,
    bulk_delete_entries,
    clear_entry_bulk_selection,
    select_visible_entries,
    set_entry_bulk_selection,
)
from .register_mutation_handler import (
    create_entry,
    delete_entry,
    generate_entity_code,
    update_entry,
)
from .register_export_handler import export_register

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementRegisterWorkspaceController(
    RegisterStateSettersMixin, ProjectManagementWorkspaceControllerBase
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
    entryPageChanged = Signal()
    entryPageSizeChanged = Signal()
    entryTotalCountChanged = Signal()
    selectedEntryIdsChanged = Signal()
    selectedEntryCountChanged = Signal()

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
        self._overview: dict[str, object] = default_overview()
        self._project_options: list[dict[str, str]] = []
        self._type_options: list[dict[str, str]] = []
        self._status_options: list[dict[str, str]] = []
        self._severity_options: list[dict[str, str]] = []
        self._selected_project_id = "all"
        self._selected_type_filter = "all"
        self._selected_status_filter = "all"
        self._selected_severity_filter = "all"
        self._search_text = ""
        self._table_models: RegisterTableModels = create_register_table_models(self)
        self._entries: dict[str, object] = default_entries()
        self._selected_entry: dict[str, object] = default_selected_entry()
        self._selected_entry_id = ""
        self._urgent_entries: dict[str, object] = default_urgent_entries()
        self._entry_page = 1
        self._entry_page_size = 25
        self._entry_total_count = 0
        self._selected_entry_ids: list[str] = []

        bind_register_domain_events(self)
        self.refresh()

    # ── Properties ───────────────────────────────────────────────────────

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

    @Property(QObject, constant=True)
    def entriesTableModel(self) -> DynamicTableModel:
        return self._table_models.entries

    @Property("QVariantMap", notify=selectedEntryChanged)
    def selectedEntry(self) -> dict[str, object]:
        return self._selected_entry

    @Property(str, notify=selectedEntryIdChanged)
    def selectedEntryId(self) -> str:
        return self._selected_entry_id

    @Property("QVariantMap", notify=urgentEntriesChanged)
    def urgentEntries(self) -> dict[str, object]:
        return self._urgent_entries

    @Property("QVariantList", notify=statusOptionsChanged)
    def bulkStatusOptions(self) -> list[dict[str, str]]:
        return [o for o in self._status_options if str(o.get("value", "")).lower() != "all"]

    @Property(int, notify=entryPageChanged)
    def entryPage(self) -> int:
        return self._entry_page

    @Property(int, notify=entryPageSizeChanged)
    def entryPageSize(self) -> int:
        return self._entry_page_size

    @Property(int, notify=entryTotalCountChanged)
    def entryTotalCount(self) -> int:
        return self._entry_total_count

    @Property("QVariantList", notify=selectedEntryIdsChanged)
    def selectedEntryIds(self) -> list[str]:
        return self._selected_entry_ids

    @Property(int, notify=selectedEntryCountChanged)
    def selectedEntryCount(self) -> int:
        return len(self._selected_entry_ids)

    # ── Core ─────────────────────────────────────────────────────────────

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
            self._set_entry_total_count(len(self._entries.get("items") or []))
            self._set_selected_entry_id(workspace_state.selected_entry_id)
            self._set_selected_entry(
                serialize_register_detail_view_model(
                    workspace_state.selected_entry_detail
                )
            )
            self._set_urgent_entries(
                serialize_register_collection_view_model(workspace_state.urgent_entries)
            )
            self._set_empty_state(workspace_state.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    # ── Filter / Selection ───────────────────────────────────────────────

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        select_project(self, project_id)

    @Slot(str)
    def setTypeFilter(self, type_filter: str) -> None:
        set_type_filter(self, type_filter)

    @Slot(str)
    def setStatusFilter(self, status_filter: str) -> None:
        set_status_filter(self, status_filter)

    @Slot(str)
    def setSeverityFilter(self, severity_filter: str) -> None:
        set_severity_filter(self, severity_filter)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        set_search_text(self, search_text)

    @Slot(str)
    def selectEntry(self, entry_id: str) -> None:
        select_entry(self, entry_id)

    @Slot(int)
    def setEntryPage(self, page: int) -> None:
        set_entry_page(self, page)

    @Slot(int)
    def setEntryPageSize(self, page_size: int) -> None:
        set_entry_page_size(self, page_size)

    # ── Bulk ─────────────────────────────────────────────────────────────

    @Slot(str, bool)
    def setEntryBulkSelection(self, entry_id: str, selected: bool) -> None:
        set_entry_bulk_selection(self, entry_id, selected)

    @Slot()
    def selectVisibleEntries(self) -> None:
        select_visible_entries(self)

    @Slot()
    def clearEntryBulkSelection(self) -> None:
        clear_entry_bulk_selection(self)

    @Slot("QVariantList", result="QVariantMap")
    def bulkDeleteEntries(self, entry_ids: list) -> dict[str, object]:
        return bulk_delete_entries(self, entry_ids)

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkEntryStatus(self, payload: dict[str, object]) -> dict[str, object]:
        return apply_bulk_entry_status(self, payload)

    # ── Export ───────────────────────────────────────────────────────────

    @Slot()
    def exportRegister(self) -> None:
        export_register(self)

    # ── CRUD ─────────────────────────────────────────────────────────────

    @Slot(str, "QVariantMap", result=str)
    def generateEntityCode(self, entity_type: str, payload: dict[str, object]) -> str:
        return generate_entity_code(self, entity_type, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def createEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return create_entry(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return update_entry(self, payload)

    @Slot(str, result="QVariantMap")
    def deleteEntry(self, entry_id: str) -> dict[str, object]:
        return delete_entry(self, entry_id)


__all__ = ["ProjectManagementRegisterWorkspaceController"]
