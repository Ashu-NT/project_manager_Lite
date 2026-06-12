from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_project_catalog_overview_view_model,
    serialize_project_detail_view_model,
    serialize_project_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectProjectsWorkspacePresenter,
)

from .project_state import (
    default_lazy_section,
    default_overview,
    default_projects,
    default_selected_project,
)
from .project_table_models import ProjectTableModels, create_project_table_models
from .project_state_setters import ProjectStateSettersMixin
from .project_domain_event_binder import bind_project_domain_events
from .project_selection_handler import (
    activate_project,
    select_project,
    set_project_page,
    set_project_page_size,
    set_search_text,
    set_status_filter,
)
from .project_lazy_section_loader import (
    load_project_activity,
    load_project_documents,
    load_project_financials,
    load_project_resources,
    load_project_risks,
    load_project_tasks,
)
from .project_resource_handler import (
    assign_project_resource,
    load_assignable_resources,
    remove_project_resource,
    select_project_resource,
    update_project_resource,
)
from .project_bulk_handler import (
    apply_bulk_status,
    bulk_delete_projects,
    clear_project_bulk_selection,
    select_visible_projects,
    set_project_bulk_selection,
)
from .project_export_handler import export_projects
from .project_import_handler import cancel_import, execute_import, preview_import

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementProjectsWorkspaceController(
    ProjectStateSettersMixin, ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    statusOptionsChanged = Signal()
    selectedStatusFilterChanged = Signal()
    searchTextChanged = Signal()
    projectsChanged = Signal()
    selectedProjectChanged = Signal()
    selectedProjectIdChanged = Signal()
    projectPageChanged = Signal()
    projectPageSizeChanged = Signal()
    projectTotalCountChanged = Signal()
    selectedProjectIdsChanged = Signal()
    selectedProjectCountChanged = Signal()

    projectTasksChanged = Signal()
    projectResourcesChanged = Signal()
    projectFinancialsChanged = Signal()
    projectRisksChanged = Signal()
    projectDocumentsChanged = Signal()
    projectActivityChanged = Signal()

    projectTasksLoadedChanged = Signal()
    projectResourcesLoadedChanged = Signal()
    projectFinancialsLoadedChanged = Signal()
    projectRisksLoadedChanged = Signal()
    projectDocumentsLoadedChanged = Signal()
    projectActivityLoadedChanged = Signal()

    importPreviewChanged = Signal()
    importBusyChanged = Signal()
    importErrorChanged = Signal()

    assignableResourceOptionsChanged = Signal()
    selectedProjectResourceIdChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        projects_workspace_presenter: ProjectProjectsWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.projects"
        )
        self._projects_workspace_presenter = (
            projects_workspace_presenter or ProjectProjectsWorkspacePresenter()
        )
        self._overview: dict[str, object] = default_overview()
        self._status_options: list[dict[str, str]] = []
        self._selected_status_filter = "all"
        self._search_text = ""
        self._table_models: ProjectTableModels = create_project_table_models(self)
        self._projects: dict[str, object] = default_projects()
        self._selected_project: dict[str, object] = default_selected_project()
        self._selected_project_id = ""
        self._project_page = 1
        self._project_page_size = 25
        self._project_total_count = 0
        self._selected_project_ids: list[str] = []
        self._selected_project_count = 0

        self._project_tasks: dict[str, object] = default_lazy_section("Tasks", "tasks")
        self._project_resources: dict[str, object] = default_lazy_section("Resources", "resources")
        self._project_financials: dict[str, object] = default_lazy_section("Financials", "financials")
        self._project_risks: dict[str, object] = default_lazy_section("Risks", "risks")
        self._project_documents: dict[str, object] = default_lazy_section("Documents", "documents")
        self._project_activity: dict[str, object] = default_lazy_section("Activity", "activity")

        self._project_tasks_loaded_for_project_id = ""
        self._project_resources_loaded_for_project_id = ""
        self._project_financials_loaded_for_project_id = ""
        self._project_risks_loaded_for_project_id = ""
        self._project_documents_loaded_for_project_id = ""
        self._project_activity_loaded_for_project_id = ""

        self._import_preview: dict[str, object] = {}
        self._import_busy = False
        self._import_error = ""
        self._assignable_resource_options: list[dict[str, str]] = []
        self._selected_project_resource_id = ""

        bind_project_domain_events(self)
        self.refresh()

    # ── Properties ───────────────────────────────────────────────────────

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=statusOptionsChanged)
    def statusOptions(self) -> list[dict[str, str]]:
        return self._status_options

    @Property("QVariantList", notify=statusOptionsChanged)
    def bulkStatusOptions(self) -> list[dict[str, str]]:
        return [opt for opt in self._status_options if opt.get("value", "all") != "all"]

    @Property(str, notify=selectedStatusFilterChanged)
    def selectedStatusFilter(self) -> str:
        return self._selected_status_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=projectsChanged)
    def projects(self) -> dict[str, object]:
        return self._projects

    @Property(QObject, constant=True)
    def projectsTableModel(self) -> DynamicTableModel:
        return self._table_models.projects

    @Property("QVariantMap", notify=selectedProjectChanged)
    def selectedProject(self) -> dict[str, object]:
        return self._selected_project

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str:
        return self._selected_project_id

    @Property(int, notify=projectPageChanged)
    def projectPage(self) -> int:
        return self._project_page

    @Property(int, notify=projectPageSizeChanged)
    def projectPageSize(self) -> int:
        return self._project_page_size

    @Property(int, notify=projectTotalCountChanged)
    def projectTotalCount(self) -> int:
        return self._project_total_count

    @Property("QVariantList", notify=selectedProjectIdsChanged)
    def selectedProjectIds(self) -> list[str]:
        return list(self._selected_project_ids)

    @Property(int, notify=selectedProjectCountChanged)
    def selectedProjectCount(self) -> int:
        return self._selected_project_count

    @Property("QVariantMap", notify=projectTasksChanged)
    def projectTasks(self) -> dict[str, object]:
        return self._project_tasks

    @Property(QObject, constant=True)
    def projectTasksTableModel(self) -> DynamicTableModel:
        return self._table_models.project_tasks

    @Property("QVariantMap", notify=projectResourcesChanged)
    def projectResources(self) -> dict[str, object]:
        return self._project_resources

    @Property(QObject, constant=True)
    def projectResourcesTableModel(self) -> DynamicTableModel:
        return self._table_models.project_resources

    @Property("QVariantMap", notify=projectFinancialsChanged)
    def projectFinancials(self) -> dict[str, object]:
        return self._project_financials

    @Property("QVariantMap", notify=projectRisksChanged)
    def projectRisks(self) -> dict[str, object]:
        return self._project_risks

    @Property("QVariantMap", notify=projectDocumentsChanged)
    def projectDocuments(self) -> dict[str, object]:
        return self._project_documents

    @Property("QVariantMap", notify=projectActivityChanged)
    def projectActivity(self) -> dict[str, object]:
        return self._project_activity

    @Property("QVariantMap", notify=importPreviewChanged)
    def importPreview(self) -> dict[str, object]:
        return self._import_preview

    @Property(bool, notify=importBusyChanged)
    def isImportBusy(self) -> bool:
        return self._import_busy

    @Property(str, notify=importErrorChanged)
    def importError(self) -> str:
        return self._import_error

    @Property("QVariantList", notify=assignableResourceOptionsChanged)
    def assignableResourceOptions(self) -> list[dict[str, str]]:
        return self._assignable_resource_options

    @Property(str, notify=selectedProjectResourceIdChanged)
    def selectedProjectResourceId(self) -> str:
        return self._selected_project_resource_id

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
            workspace_state = self._projects_workspace_presenter.build_workspace_state(
                search_text=self._search_text,
                status_filter=self._selected_status_filter,
                selected_project_id=self._selected_project_id or None,
                page=self._project_page,
                page_size=self._project_page_size,
            )
            self._set_overview(
                serialize_project_catalog_overview_view_model(workspace_state.overview)
            )
            self._set_status_options(
                serialize_selector_options(workspace_state.status_options)
            )
            self._set_selected_status_filter(workspace_state.selected_status_filter)
            self._set_search_text(workspace_state.search_text)
            self._set_projects(
                {
                    "title": "Project Catalog",
                    "subtitle": "Create, edit, and review project lifecycle records.",
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_project_record_view_models(
                        workspace_state.projects
                    ),
                }
            )
            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_selected_project(
                serialize_project_detail_view_model(
                    workspace_state.selected_project_detail
                )
            )
            self._set_empty_state(workspace_state.empty_state)
            self._set_project_total_count(workspace_state.total_count)
            self._set_project_page(workspace_state.page)
            self._set_project_page_size(workspace_state.page_size)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    # ── Filter / Selection ───────────────────────────────────────────────

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        set_search_text(self, search_text)

    @Slot(str)
    def setStatusFilter(self, status_filter: str) -> None:
        set_status_filter(self, status_filter)

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        select_project(self, project_id)

    @Slot(str)
    def activateProject(self, project_id: str) -> None:
        activate_project(self, project_id)

    @Slot(int)
    def setProjectPage(self, page: int) -> None:
        set_project_page(self, page)

    @Slot(int)
    def setProjectPageSize(self, page_size: int) -> None:
        set_project_page_size(self, page_size)

    # ── Bulk ─────────────────────────────────────────────────────────────

    @Slot(str, bool)
    def setProjectBulkSelection(self, project_id: str, selected: bool) -> None:
        set_project_bulk_selection(self, project_id, selected)

    @Slot()
    def clearProjectBulkSelection(self) -> None:
        clear_project_bulk_selection(self)

    @Slot()
    def selectVisibleProjects(self) -> None:
        select_visible_projects(self)

    @Slot("QVariantList", result="QVariantMap")
    def bulkDeleteProjects(self, project_ids: list) -> dict[str, object]:
        return bulk_delete_projects(self, project_ids)

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkStatus(self, payload: dict[str, object]) -> dict[str, object]:
        return apply_bulk_status(self, payload)

    # ── Export / Import ──────────────────────────────────────────────────

    @Slot("QVariantList", str, result="QVariantMap")
    def exportProjects(self, columns: list, file_path: str) -> dict[str, object]:
        return export_projects(self, columns, file_path)

    @Slot(str, str, result="QVariantMap")
    def previewImport(self, file_path: str, source_format: str) -> dict[str, object]:
        return preview_import(self, file_path, source_format)

    @Slot(str, result="QVariantMap")
    def executeImport(self, session_id: str) -> dict[str, object]:
        return execute_import(self, session_id)

    @Slot()
    def cancelImport(self) -> None:
        cancel_import(self)

    # ── CRUD ─────────────────────────────────────────────────────────────

    @Slot(str, "QVariantMap", result=str)
    def generateEntityCode(self, entity_type: str, payload: dict[str, object]) -> str:
        if (entity_type or "").strip().lower() != "project":
            return ""
        try:
            return self._projects_workspace_presenter.suggest_code(dict(payload))
        except Exception as exc:
            self._set_error_message(str(exc))
            return ""

    @Slot("QVariantMap", result="QVariantMap")
    def createProject(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.create_project(dict(payload)),
            success_message="Project created.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateProject(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.update_project(dict(payload)),
            success_message="Project updated.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, str, result="QVariantMap")
    def setProjectStatus(self, project_id: str, status: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.set_project_status(project_id, status),
            success_message="Project status updated.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteProject(self, project_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.delete_project(project_id),
            success_message="Project deleted.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    # ── Lazy Sections ────────────────────────────────────────────────────

    @Slot()
    def loadProjectTasks(self) -> None:
        load_project_tasks(self)

    @Slot()
    def loadProjectResources(self) -> None:
        load_project_resources(self)

    @Slot()
    def loadProjectFinancials(self) -> None:
        load_project_financials(self)

    @Slot()
    def loadProjectRisks(self) -> None:
        load_project_risks(self)

    @Slot()
    def loadProjectDocuments(self) -> None:
        load_project_documents(self)

    @Slot()
    def loadProjectActivity(self) -> None:
        load_project_activity(self)

    # ── Resources ────────────────────────────────────────────────────────

    @Slot()
    def loadAssignableResources(self) -> None:
        load_assignable_resources(self)

    @Slot(str)
    def selectProjectResource(self, project_resource_id: str) -> None:
        select_project_resource(self, project_resource_id)

    @Slot("QVariantMap", result="QVariantMap")
    def assignProjectResource(self, payload: dict[str, object]) -> dict[str, object]:
        return assign_project_resource(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateProjectResource(self, payload: dict[str, object]) -> dict[str, object]:
        return update_project_resource(self, payload)

    @Slot(str, result="QVariantMap")
    def removeProjectResource(self, project_resource_id: str) -> dict[str, object]:
        return remove_project_resource(self, project_resource_id)


__all__ = ["ProjectManagementProjectsWorkspaceController"]
