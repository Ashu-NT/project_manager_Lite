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

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementProjectsWorkspaceController(
    ProjectManagementWorkspaceControllerBase
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
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._status_options: list[dict[str, str]] = []
        self._selected_status_filter = "all"
        self._search_text = ""
        self._projects_table_model = DynamicTableModel(self)
        self._projects: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_project: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._selected_project_id = ""
        self._project_page = 1
        self._project_page_size = 25
        self._project_total_count = 0
        self._selected_project_ids: list[str] = []
        self._selected_project_count = 0
        
        self._project_tasks_table_model = DynamicTableModel(self)
        self._project_resources_table_model = DynamicTableModel(self)
        self._project_tasks = {"title": "Tasks", "subtitle": "", "emptyState": "Open this section to load project tasks.", "items": []}
        self._project_resources = {"title": "Resources", "subtitle": "", "emptyState": "Open this section to load project resources.", "items": []}
        self._project_financials = {"title": "Financials", "subtitle": "", "emptyState": "Open this section to load project financials.", "items": []}
        self._project_risks = {"title": "Risks", "subtitle": "", "emptyState": "Open this section to load project risks.", "items": []}
        self._project_documents = {"title": "Documents", "subtitle": "", "emptyState": "Open this section to load project documents.", "items": []}
        self._project_activity = {"title": "Activity", "subtitle": "", "emptyState": "Open this section to load project activity.", "items": []}

        self._project_tasks_loaded_for_project_id = ""
        self._project_resources_loaded_for_project_id = ""
        self._project_financials_loaded_for_project_id = ""
        self._project_risks_loaded_for_project_id = ""
        self._project_documents_loaded_for_project_id = ""
        self._project_activity_loaded_for_project_id = ""

        self._import_preview: dict[str, object] = {}
        self._import_busy = False
        self._import_error = ""

        self._bind_domain_events()
        self.refresh()

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
        return self._projects_table_model

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
        return self._project_tasks_table_model

    @Property("QVariantMap", notify=projectResourcesChanged)
    def projectResources(self) -> dict[str, object]:
        return self._project_resources

    @Property(QObject, constant=True)
    def projectResourcesTableModel(self) -> DynamicTableModel:
        return self._project_resources_table_model

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
                serialize_project_catalog_overview_view_model(
                    workspace_state.overview
                )
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

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized_value = (search_text or "").strip()
        if normalized_value == self._search_text:
            return
        self._set_search_text(normalized_value)
        self._project_page = 1
        self.refresh()

    @Slot(str)
    def setStatusFilter(self, status_filter: str) -> None:
        normalized_value = (status_filter or "").strip().lower() or "all"
        if normalized_value == self._selected_status_filter.lower():
            return
        self._set_selected_status_filter(normalized_value)
        self._project_page = 1
        self.refresh()

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        normalized_value = (project_id or "").strip()
        if normalized_value == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_value)

    @Slot(str)
    def activateProject(self, project_id: str) -> None:
        normalized_value = (project_id or "").strip()

        if not normalized_value:
            return

        self._set_selected_project_id(normalized_value)
        self._reset_project_lazy_sections()
        
        self._set_is_loading(True)

        try:
            self._set_error_message("")

            workspace_state = self._projects_workspace_presenter.build_project_detail_state(
                project_id=normalized_value,
            )

            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_selected_project(
                serialize_project_detail_view_model(
                    workspace_state.selected_project_detail
                )
            )

        except Exception as exc:
            self._set_error_message(str(exc))

        finally:
            self._set_is_loading(False)

    @Slot(int)
    def setProjectPage(self, page: int) -> None:
        p = max(1, page)
        if p == self._project_page:
            return
        self._set_project_page(p)
        self.refresh()

    @Slot(int)
    def setProjectPageSize(self, page_size: int) -> None:
        if page_size <= 0 or page_size == self._project_page_size:
            return
        self._project_page_size = page_size
        self.projectPageSizeChanged.emit()
        self._set_project_page(1)
        self.refresh()

    @Slot(str, bool)
    def setProjectBulkSelection(self, project_id: str, selected: bool) -> None:
        normalized_id = (project_id or "").strip()
        if not normalized_id:
            return
        current = list(self._selected_project_ids)
        if selected and normalized_id not in current:
            current.append(normalized_id)
        elif not selected and normalized_id in current:
            current.remove(normalized_id)
        else:
            return
        self._set_selected_project_ids(current)

    @Slot()
    def clearProjectBulkSelection(self) -> None:
        self._set_selected_project_ids([])

    @Slot()
    def selectVisibleProjects(self) -> None:
        items = self._projects.get("items") or []
        visible_ids = [
            str(item.get("id", "") or "")
            for item in items
            if item.get("id")
        ]
        self._set_selected_project_ids(visible_ids)

    @Slot("QVariantList", result="QVariantMap")
    def bulkDeleteProjects(self, project_ids: list) -> dict[str, object]:
        ids = [str(pid) for pid in (project_ids or []) if pid]
        if not ids:
            return {}
        return run_mutation(
            operation=lambda: self._do_bulk_delete(ids),
            success_message=f"{len(ids)} project(s) deleted.",
            on_success=self._on_bulk_mutation_success,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkStatus(self, payload: dict[str, object]) -> dict[str, object]:
        status_value = str(payload.get("status", "") or "").strip()
        ids = list(self._selected_project_ids)
        if not status_value or not ids:
            return {}
        return run_mutation(
            operation=lambda: self._do_bulk_set_status(ids, status_value),
            success_message=f"{len(ids)} project(s) updated.",
            on_success=self._on_bulk_mutation_success,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantList", str, result="QVariantMap")
    def exportProjects(self, columns: list, file_path: str) -> dict[str, object]:
        from src.ui_qml.modules.project_management.utils.table_exporter import export_to_file
        self._set_error_message("")
        try:
            all_ws = self._projects_workspace_presenter.build_workspace_state(
                search_text=self._search_text,
                status_filter=self._selected_status_filter,
                selected_project_id=None,
                page=1,
                page_size=99999,
            )
            rows = serialize_project_record_view_models(all_ws.projects)
            result = export_to_file(rows, list(columns), (file_path or "").strip())
            if result.get("ok"):
                self._set_feedback_message(result.get("message", "Export complete."))
            else:
                self._set_error_message(result.get("error", "Export failed."))
            return result
        except Exception as exc:
            self._set_error_message(str(exc))
            return {"ok": False, "error": str(exc)}

    @Slot(str, str, result="QVariantMap")
    def previewImport(self, file_path: str, source_format: str) -> dict[str, object]:
        self._set_import_busy(True)
        self._set_import_error("")
        try:
            preview = self._projects_workspace_presenter.preview_import(
                file_path=file_path,
                source_format=source_format,
            )
            self._set_import_preview(preview)
            return {"ok": True}
        except Exception as exc:
            self._set_import_error(str(exc))
            return {"ok": False, "error": str(exc)}
        finally:
            self._set_import_busy(False)

    @Slot(str, result="QVariantMap")
    def executeImport(self, session_id: str) -> dict[str, object]:
        self._set_import_busy(True)
        self._set_import_error("")
        try:
            result = self._projects_workspace_presenter.execute_import(
                session_id=session_id,
            )
            self._set_feedback_message(result.get("message", "Import completed."))
            self._set_import_preview({})
            return result
        except Exception as exc:
            self._set_import_error(str(exc))
            return {"ok": False, "error": str(exc)}
        finally:
            self._set_import_busy(False)

    @Slot()
    def cancelImport(self) -> None:
        self._set_import_preview({})
        self._set_import_error("")

    @Slot("QVariantMap", result="QVariantMap")
    def createProject(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.create_project(
                dict(payload)
            ),
            success_message="Project created.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateProject(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.update_project(
                dict(payload)
            ),
            success_message="Project updated.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, str, result="QVariantMap")
    def setProjectStatus(
        self,
        project_id: str,
        status: str,
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.set_project_status(
                project_id,
                status,
            ),
            success_message="Project status updated.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteProject(self, project_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.delete_project(
                project_id
            ),
            success_message="Project deleted.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot()
    def loadProjectTasks(self) -> None:
        if not self._selected_project_id:
            return
        if self._project_tasks_loaded_for_project_id == self._selected_project_id:
            return

        self._set_is_loading(True)
        try:
            self._clear_section_error("tasks")
            ws = self._projects_workspace_presenter.build_project_tasks_state(
                project_id=self._selected_project_id
            )
            self._set_project_tasks(self._serialize_project_section(ws.project_tasks))
            self._project_tasks_loaded_for_project_id = self._selected_project_id
        except Exception as exc:
            self._set_section_error("tasks", str(exc))
        finally:
            self._set_is_loading(False)

    @Slot()
    def loadProjectResources(self) -> None:
        if not self._selected_project_id:
            return
        if self._project_resources_loaded_for_project_id == self._selected_project_id:
            return

        self._set_is_loading(True)
        try:
            self._clear_section_error("resources")
            ws = self._projects_workspace_presenter.build_project_resources_state(
                project_id=self._selected_project_id
            )
            self._set_project_resources(self._serialize_project_section(ws.project_resources))
            self._project_resources_loaded_for_project_id = self._selected_project_id
        except Exception as exc:
            self._set_section_error("resources", str(exc))
        finally:
            self._set_is_loading(False)

    @Slot()
    def loadProjectFinancials(self) -> None:
        if not self._selected_project_id:
            return
        if self._project_financials_loaded_for_project_id == self._selected_project_id:
            return

        self._set_is_loading(True)
        try:
            self._clear_section_error("financials")
            ws = self._projects_workspace_presenter.build_project_financials_state(
                project_id=self._selected_project_id
            )
            self._set_project_financials(self._serialize_project_section(ws.project_financials))
            self._project_financials_loaded_for_project_id = self._selected_project_id
        except Exception as exc:
            self._set_section_error("financials", str(exc))
        finally:
            self._set_is_loading(False)

    @Slot()
    def loadProjectRisks(self) -> None:
        if not self._selected_project_id:
            return
        if self._project_risks_loaded_for_project_id == self._selected_project_id:
            return

        self._set_is_loading(True)
        try:
            self._clear_section_error("risks")
            ws = self._projects_workspace_presenter.build_project_risks_state(
                project_id=self._selected_project_id
            )
            self._set_project_risks(self._serialize_project_section(ws.project_risks))
            self._project_risks_loaded_for_project_id = self._selected_project_id
        except Exception as exc:
            self._set_section_error("risks", str(exc))
        finally:
            self._set_is_loading(False)

    @Slot()
    def loadProjectDocuments(self) -> None:
        if not self._selected_project_id:
            return
        if self._project_documents_loaded_for_project_id == self._selected_project_id:
            return

        self._set_is_loading(True)
        try:
            self._clear_section_error("documents")
            ws = self._projects_workspace_presenter.build_project_documents_state(
                project_id=self._selected_project_id
            )
            self._set_project_documents(self._serialize_project_section(ws.project_documents))
            self._project_documents_loaded_for_project_id = self._selected_project_id
        except Exception as exc:
            self._set_section_error("documents", str(exc))
        finally:
            self._set_is_loading(False)

    @Slot()
    def loadProjectActivity(self) -> None:
        if not self._selected_project_id:
            return
        if self._project_activity_loaded_for_project_id == self._selected_project_id:
            return

        self._set_is_loading(True)
        try:
            self._clear_section_error("activity")
            ws = self._projects_workspace_presenter.build_project_activity_state(
                project_id=self._selected_project_id
            )
            self._set_project_activity(self._serialize_project_section(ws.project_activity))
            self._project_activity_loaded_for_project_id = self._selected_project_id
        except Exception as exc:
            self._set_section_error("activity", str(exc))
        finally:
            self._set_is_loading(False)

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "portfolio_entity",
            scope_code="project_management",
        )

    def _reset_project_lazy_sections(self) -> None:
        self._project_tasks_loaded_for_project_id = ""
        self._project_resources_loaded_for_project_id = ""
        self._project_financials_loaded_for_project_id = ""
        self._project_risks_loaded_for_project_id = ""
        self._project_documents_loaded_for_project_id = ""
        self._project_activity_loaded_for_project_id = ""

    def _on_bulk_mutation_success(self) -> None:
        self._set_selected_project_ids([])
        self._request_domain_refresh()

    def _do_bulk_delete(self, ids: list[str]) -> None:
        for project_id in ids:
            self._projects_workspace_presenter.delete_project(project_id)

    def _do_bulk_set_status(self, ids: list[str], status: str) -> None:
        for project_id in ids:
            self._projects_workspace_presenter.set_project_status(project_id, status)

    @staticmethod
    def _serialize_project_section(section) -> dict[str, object]:
        return {
            "title": section.title,
            "subtitle": section.subtitle,
            "emptyState": section.empty_state,
            "items": serialize_project_record_view_models(section.items),
        }

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
        self._projects_table_model.set_rows(projects.get("items", []))
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
        self._project_tasks_table_model.set_rows(value.get("items", []))
        self.projectTasksChanged.emit()

    def _set_project_resources(self, value: dict[str, object]) -> None:
        if value == self._project_resources:
            return
        self._project_resources = value
        self._project_resources_table_model.set_rows(value.get("items", []))
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

__all__ = ["ProjectManagementProjectsWorkspaceController"]
