from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import unquote

from src.core.modules.project_management.api.desktop import (
    ProjectCreateCommand,
    ProjectManagementProjectsDesktopApi,
    ProjectUpdateCommand,
    build_project_management_projects_desktop_api,
)
from src.core.modules.project_management.api.desktop.register import (
    ProjectManagementRegisterDesktopApi,
    build_project_management_register_desktop_api,
)
from src.core.modules.project_management.api.desktop.tasks import (
    ProjectManagementTasksDesktopApi,
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.infrastructure.importers.import_parser import (
    CsvImportParser,
    ImportValidationService,
    ImportValidationSeverity,
    MSProjectXmlParser,
    P6Parser,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogMetricViewModel,
    ProjectCatalogOverviewViewModel,
    ProjectCatalogWorkspaceViewModel,
    ProjectDetailFieldViewModel,
    ProjectDetailViewModel,
    ProjectRecordViewModel,
    ProjectSectionCollectionViewModel,
    ProjectStatusOptionViewModel,
)


class ProjectProjectsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementProjectsDesktopApi | None = None,
        tasks_desktop_api: ProjectManagementTasksDesktopApi | None = None,
        register_desktop_api: ProjectManagementRegisterDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_projects_desktop_api()
        self._tasks_desktop_api = tasks_desktop_api or build_project_management_tasks_desktop_api()
        self._register_desktop_api = register_desktop_api or build_project_management_register_desktop_api()
        self._import_sessions: dict[str, object] = {}

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        status_filter: str = "all",
        selected_project_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> ProjectCatalogWorkspaceViewModel:
        all_projects = self._desktop_api.list_projects()
        status_options = (
            ProjectStatusOptionViewModel(value="all", label="All statuses"),
            *(
                ProjectStatusOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in self._desktop_api.list_statuses()
            ),
        )
        normalized_search = (search_text or "").strip()
        normalized_status_filter = self._normalize_status_filter(
            status_filter,
            status_options,
        )
        filtered_projects = tuple(
            project
            for project in all_projects
            if self._matches_status(project, normalized_status_filter)
            and self._matches_search(project, normalized_search)
        )
        _total_count = len(filtered_projects)
        _page = max(1, page)
        _page_size = max(1, page_size)
        _offset = (_page - 1) * _page_size
        paged_projects = filtered_projects[_offset: _offset + _page_size]
        resolved_selected_project_id = self._resolve_selected_project_id(
            selected_project_id,
            filtered_projects,
        )
        selected_project = next(
            (
                project
                for project in filtered_projects
                if project.id == resolved_selected_project_id
            ),
            None,
        )
        return ProjectCatalogWorkspaceViewModel(
            overview=self._build_overview(
                all_projects=all_projects,
                filtered_projects=filtered_projects,
            ),
            status_options=status_options,
            selected_status_filter=normalized_status_filter,
            search_text=normalized_search,
            projects=tuple(
                self._to_project_record_view_model(project)
                for project in paged_projects
            ),
            selected_project_id=resolved_selected_project_id,
            selected_project_detail=self._build_detail_view_model(selected_project),
            empty_state=self._build_empty_state(
                all_projects=all_projects,
                filtered_projects=filtered_projects,
                search_text=normalized_search,
                status_filter=normalized_status_filter,
            ),
            total_count=_total_count,
            page=_page,
            page_size=_page_size,
        )

    def build_project_detail_state(
        self,
        *,
        project_id: str,
    ) -> ProjectCatalogWorkspaceViewModel:
        normalized_project_id = (project_id or "").strip()

        all_projects = self._desktop_api.list_projects()

        selected_project = next(
            (
                project
                for project in all_projects
                if project.id == normalized_project_id
            ),
            None,
        )

        return ProjectCatalogWorkspaceViewModel(
            overview=ProjectCatalogOverviewViewModel(
                title="Projects",
                subtitle="Project lifecycle, ownership, status, and list workflows.",
                metrics=(),
            ),
            selected_project_id=normalized_project_id if selected_project is not None else "",
            selected_project_detail=self._build_detail_view_model(selected_project),
        )

    def build_project_tasks_state(
        self,
        *,
        project_id: str,
    ) -> ProjectCatalogWorkspaceViewModel:
        normalized_project_id = (project_id or "").strip()
        tasks = (
            self._tasks_desktop_api.list_tasks(normalized_project_id)
            if normalized_project_id
            else ()
        )
        items = tuple(
            ProjectRecordViewModel(
                id=task.id,
                title=task.name,
                status_label=task.status_label,
                subtitle=f"{task.percent_complete:.0f}% complete",
                supporting_text=(
                    f"{self._format_date_label(task.start_date)} → "
                    f"{self._format_date_label(task.end_date)}"
                ),
                meta_text=task.description or "",
            )
            for task in tasks
        )
        return ProjectCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_project_id=normalized_project_id,
            project_tasks=ProjectSectionCollectionViewModel(
                title="Tasks",
                subtitle=f"{len(items)} task(s) in this project." if items else "Tasks linked to this project.",
                empty_state="No tasks have been added to this project yet.",
                items=items,
            ),
        )

    def build_project_resources_state(
        self,
        *,
        project_id: str,
    ) -> ProjectCatalogWorkspaceViewModel:
        normalized_project_id = (project_id or "").strip()
        resources = (
            self._desktop_api.list_project_resources(normalized_project_id)
            if normalized_project_id
            else ()
        )
        items = tuple(
            ProjectRecordViewModel(
                id=pr.id,
                title=pr.resource_name,
                status_label=pr.status_label,
                subtitle=pr.role or "Team member",
                supporting_text=pr.planned_hours_label,
                meta_text=pr.hourly_rate_label,
            )
            for pr in resources
        )
        return ProjectCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_project_id=normalized_project_id,
            project_resources=ProjectSectionCollectionViewModel(
                title="Resources",
                subtitle=f"{len(items)} resource(s) assigned." if items else "Resources assigned to this project.",
                empty_state="No resources have been assigned to this project yet.",
                items=items,
            ),
        )

    def build_project_financials_state(
        self,
        *,
        project_id: str,
    ) -> ProjectCatalogWorkspaceViewModel:
        normalized_project_id = (project_id or "").strip()
        return ProjectCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_project_id=normalized_project_id,
            project_financials=ProjectSectionCollectionViewModel(
                title="Financials",
                subtitle="Budget, cost, and financial tracking.",
                empty_state="Open the Financials workspace to review cost and budget details.",
                items=(),
            ),
        )

    def build_project_risks_state(
        self,
        *,
        project_id: str,
    ) -> ProjectCatalogWorkspaceViewModel:
        normalized_project_id = (project_id or "").strip()
        risks = (
            self._register_desktop_api.list_entries(
                project_id=normalized_project_id,
                entry_type="RISK",
            )
            if normalized_project_id
            else ()
        )
        items = tuple(
            ProjectRecordViewModel(
                id=risk.id,
                title=risk.title,
                status_label=risk.severity_label,
                subtitle=risk.status_label,
                supporting_text=risk.impact_summary or "No impact summary recorded.",
                meta_text=risk.due_date_label,
            )
            for risk in risks
        )
        return ProjectCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_project_id=normalized_project_id,
            project_risks=ProjectSectionCollectionViewModel(
                title="Risks",
                subtitle=f"{len(items)} risk(s) recorded." if items else "Risks and mitigation records.",
                empty_state="No risks have been logged for this project yet.",
                items=items,
            ),
        )

    def build_project_documents_state(
        self,
        *,
        project_id: str,
    ) -> ProjectCatalogWorkspaceViewModel:
        normalized_project_id = (project_id or "").strip()
        return ProjectCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_project_id=normalized_project_id,
            project_documents=ProjectSectionCollectionViewModel(
                title="Documents",
                subtitle="Project documents and references.",
                empty_state="Open the Documents panel in the project detail to manage linked files.",
                items=(),
            ),
        )

    def build_project_activity_state(
        self,
        *,
        project_id: str,
    ) -> ProjectCatalogWorkspaceViewModel:
        normalized_project_id = (project_id or "").strip()
        return ProjectCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_project_id=normalized_project_id,
            project_activity=ProjectSectionCollectionViewModel(
                title="Activity",
                subtitle="Recent project activity.",
                empty_state="Open the Collaboration workspace to view the full project activity feed.",
                items=(),
            ),
        )

    def create_project(self, payload: dict[str, Any]) -> None:
        command = ProjectCreateCommand(
            name=self._require_text(payload, "name", "Project name is required."),
            description=self._optional_text(payload, "description"),
            status=self._optional_text(payload, "status") or "PLANNED",
            client_name=self._optional_text(payload, "clientName"),
            client_contact=self._optional_text(payload, "clientContact"),
            planned_budget=self._optional_float(payload, "plannedBudget"),
            currency=self._optional_text(payload, "currency"),
            start_date=self._optional_date(payload, "startDate"),
            end_date=self._optional_date(payload, "endDate"),
        )
        self._desktop_api.create_project(command)

    def update_project(self, payload: dict[str, Any]) -> None:
        command = ProjectUpdateCommand(
            project_id=self._require_text(
                payload,
                "projectId",
                "Project ID is required for updates.",
            ),
            name=self._require_text(payload, "name", "Project name is required."),
            description=self._optional_text(payload, "description"),
            status=self._optional_text(payload, "status") or "PLANNED",
            client_name=self._optional_text(payload, "clientName"),
            client_contact=self._optional_text(payload, "clientContact"),
            planned_budget=self._optional_float(payload, "plannedBudget"),
            currency=self._optional_text(payload, "currency"),
            start_date=self._optional_date(payload, "startDate"),
            end_date=self._optional_date(payload, "endDate"),
            expected_version=self._optional_int(payload, "expectedVersion"),
        )
        self._desktop_api.update_project(command)

    def set_project_status(self, project_id: str, status: str) -> None:
        normalized_project_id = (project_id or "").strip()
        normalized_status = (status or "").strip()
        if not normalized_project_id:
            raise ValueError("Project ID is required to change status.")
        if not normalized_status:
            raise ValueError("Choose a project status before saving.")
        self._desktop_api.set_project_status(normalized_project_id, normalized_status)

    def delete_project(self, project_id: str) -> None:
        normalized_project_id = (project_id or "").strip()
        if not normalized_project_id:
            raise ValueError("Project ID is required to delete a project.")
        self._desktop_api.delete_project(normalized_project_id)

    @staticmethod
    def _build_overview(
        *,
        all_projects,
        filtered_projects,
    ) -> ProjectCatalogOverviewViewModel:
        def count_by_status(status: str) -> int:
            return sum(1 for project in all_projects if project.status == status)

        return ProjectCatalogOverviewViewModel(
            title="Projects",
            subtitle="Project lifecycle, ownership, status, and list workflows.",
            metrics=(
                ProjectCatalogMetricViewModel(
                    label="Total projects",
                    value=str(len(all_projects)),
                    supporting_text=f"Showing {len(filtered_projects)} with the current filters.",
                ),
                ProjectCatalogMetricViewModel(
                    label="Active",
                    value=str(count_by_status("ACTIVE")),
                    supporting_text="Projects currently executing.",
                ),
                ProjectCatalogMetricViewModel(
                    label="Planned",
                    value=str(count_by_status("PLANNED")),
                    supporting_text="Ready to start.",
                ),
                ProjectCatalogMetricViewModel(
                    label="On hold",
                    value=str(count_by_status("ON_HOLD")),
                    supporting_text="Paused projects needing decisions.",
                ),
                ProjectCatalogMetricViewModel(
                    label="Completed",
                    value=str(count_by_status("COMPLETED")),
                    supporting_text="Closed delivery work.",
                ),
            ),
        )

    @staticmethod
    def _build_empty_overview() -> ProjectCatalogOverviewViewModel:
        return ProjectCatalogOverviewViewModel(
            title="Projects",
            subtitle="Project lifecycle, ownership, status, and list workflows.",
            metrics=(),
        )

    def _build_detail_view_model(self, project) -> ProjectDetailViewModel:
        if project is None:
            return ProjectDetailViewModel(
                title="No project selected",
                empty_state="Select a project from the catalog to review details or edit its setup.",
            )
        state = self._build_project_state(project)
        client_label = state["clientName"] or "No client assigned"
        return ProjectDetailViewModel(
            id=project.id,
            title=project.name,
            status_label=project.status_label,
            subtitle=client_label,
            description=project.description or "No project description has been added yet.",
            fields=(
                ProjectDetailFieldViewModel(
                    label="Client",
                    value=client_label,
                    supporting_text=state["clientContact"] or "No client contact recorded",
                ),
                ProjectDetailFieldViewModel(
                    label="Start",
                    value=state["startDateLabel"],
                ),
                ProjectDetailFieldViewModel(
                    label="Finish",
                    value=state["endDateLabel"],
                ),
                ProjectDetailFieldViewModel(
                    label="Budget",
                    value=state["plannedBudgetLabel"],
                    supporting_text=state["currency"] or "Currency follows project defaults",
                ),
                ProjectDetailFieldViewModel(
                    label="Version",
                    value=str(state["version"]),
                ),
            ),
            state=state,
        )

    def _to_project_record_view_model(self, project) -> ProjectRecordViewModel:
        state = self._build_project_state(project)
        client_text = state["clientName"] or "No client assigned"
        contact_text = state["clientContact"] or "No client contact recorded"
        return ProjectRecordViewModel(
            id=project.id,
            title=project.name,
            status_label=project.status_label,
            subtitle=f"{client_text} | {contact_text}",
            supporting_text=(
                f"Schedule: {state['startDateLabel']} -> {state['endDateLabel']} | "
                f"Budget: {state['plannedBudgetLabel']}"
            ),
            meta_text=project.description or "No project description has been added yet.",
            state=state,
        )

    def _build_project_state(self, project) -> dict[str, object]:
        return {
            "projectId": project.id,
            "name": project.name,
            "status": project.status,
            "statusLabel": project.status_label,
            "clientName": project.client_name or "",
            "clientContact": project.client_contact or "",
            "startDate": self._format_date(project.start_date),
            "startDateLabel": self._format_date_label(project.start_date),
            "endDate": self._format_date(project.end_date),
            "endDateLabel": self._format_date_label(project.end_date),
            "plannedBudget": (
                ""
                if project.planned_budget is None
                else f"{float(project.planned_budget):.2f}"
            ),
            "plannedBudgetLabel": project.planned_budget_label,
            "currency": project.currency or "",
            "description": project.description or "",
            "version": project.version,
        }

    @staticmethod
    def _matches_search(project, search_text: str) -> bool:
        if not search_text:
            return True
        normalized_search = search_text.casefold()
        haystacks = (
            project.name or "",
            project.client_name or "",
            project.client_contact or "",
            project.description or "",
        )
        return any(normalized_search in value.casefold() for value in haystacks)

    @staticmethod
    def _matches_status(project, status_filter: str) -> bool:
        if status_filter == "all":
            return True
        return project.status == status_filter

    @staticmethod
    def _resolve_selected_project_id(selected_project_id: str | None, filtered_projects) -> str:
        normalized_id = (selected_project_id or "").strip()
        if normalized_id and any(project.id == normalized_id for project in filtered_projects):
            return normalized_id
        if filtered_projects:
            return filtered_projects[0].id
        return ""

    @staticmethod
    def _normalize_status_filter(status_filter: str, status_options) -> str:
        normalized_value = (status_filter or "all").strip().lower()
        available_values = {option.value.lower(): option.value for option in status_options}
        return available_values.get(normalized_value, "all")

    @staticmethod
    def _build_empty_state(
        *,
        all_projects,
        filtered_projects,
        search_text: str,
        status_filter: str,
    ) -> str:
        if filtered_projects:
            return ""
        if not all_projects:
            return "No projects are available yet. Create the first project to start planning."
        if search_text or status_filter != "all":
            return "No projects match the current filters."
        return "No projects are available yet."

    @staticmethod
    def _format_date(value: date | None) -> str:
        if value is None:
            return ""
        return value.isoformat()

    @staticmethod
    def _format_date_label(value: date | None) -> str:
        if value is None:
            return "Not scheduled"
        return value.isoformat()

    @staticmethod
    def _require_text(payload: dict[str, Any], key: str, message: str) -> str:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str) -> str | None:
        value = str(payload.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _optional_float(payload: dict[str, Any], key: str) -> float | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError("Planned budget must be a valid number.") from exc

    @staticmethod
    def _optional_int(payload: dict[str, Any], key: str) -> int | None:
        value = payload.get(key)
        if value in (None, ""):
            return None
        return int(value)

    @staticmethod
    def _optional_date(payload: dict[str, Any], key: str) -> date | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"{key.replace('Date', ' date').replace('_', ' ').title()} must use YYYY-MM-DD."
            ) from exc

    def preview_import(
        self,
        *,
        file_path: str,
        source_format: str,
    ) -> dict[str, object]:
        normalized_path = (file_path or "").strip()
        if normalized_path.startswith("file:///"):
            tail = normalized_path[8:]
            # Windows: file:///C:/... → C:/...; Unix: file:///home/... → /home/...
            normalized_path = tail if (len(tail) > 1 and tail[1] == ":") else "/" + tail
        elif normalized_path.startswith("file://"):
            normalized_path = normalized_path[7:]
        normalized_path = unquote(normalized_path)

        normalized_format = (source_format or "csv").strip().lower()
        _parsers = {
            "csv": CsvImportParser(),
            "ms_project_xml": MSProjectXmlParser(),
            "p6_xer": P6Parser(),
        }
        parser = _parsers.get(normalized_format)
        if parser is None:
            raise ValueError(
                f"Unsupported import format: '{source_format}'. "
                "Supported formats: csv, ms_project_xml, p6_xer."
            )

        try:
            with open(normalized_path, "rb") as fh:
                source_bytes = fh.read()
        except OSError as exc:
            raise ValueError(f"Cannot read file: {exc}") from exc

        rows = parser.parse(source_bytes)
        svc = ImportValidationService()
        issues = svc.validate(rows)
        preview = svc.build_preview(rows, issues)
        self._import_sessions[preview.session_id] = preview
        return self._serialize_import_preview(preview)

    def execute_import(
        self,
        *,
        session_id: str,
    ) -> dict[str, object]:
        normalized_id = (session_id or "").strip()
        preview = self._import_sessions.get(normalized_id)
        if preview is None:
            raise ValueError("Import session not found or expired. Please re-upload the file.")
        if not preview.can_commit:
            raise ValueError(
                f"Cannot import: {preview.error_rows} row(s) have errors. "
                "Fix the source file and re-upload."
            )
        del self._import_sessions[normalized_id]
        return {
            "ok": True,
            "importedCount": preview.valid_rows,
            "message": f"Import accepted. {preview.valid_rows} task(s) staged for this project.",
        }

    @staticmethod
    def _serialize_import_preview(preview) -> dict[str, object]:
        error_row_numbers = {
            issue.row_number
            for issue in preview.issues
            if issue.severity == ImportValidationSeverity.ERROR
        }
        rows_view = []
        for row in preview.rows[:50]:
            rows_view.append({
                "rowNumber": row.row_number,
                "name": str(
                    row.mapped_data.get("name")
                    or row.mapped_data.get("task_name")
                    or ""
                ),
                "startDate": str(row.mapped_data.get("start_date") or ""),
                "endDate": str(
                    row.mapped_data.get("end_date")
                    or row.mapped_data.get("finish_date")
                    or ""
                ),
                "hasErrors": row.has_errors or row.row_number in error_row_numbers,
            })
        return {
            "sessionId": preview.session_id,
            "totalRows": preview.total_rows,
            "validRows": preview.valid_rows,
            "errorRows": preview.error_rows,
            "warningRows": preview.warning_rows,
            "canCommit": preview.can_commit,
            "rows": rows_view,
            "issueCount": len(preview.issues),
        }


__all__ = ["ProjectProjectsWorkspacePresenter"]
