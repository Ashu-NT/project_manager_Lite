from __future__ import annotations

from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectCreateCommand,
    ProjectManagementProjectsDesktopApi,
    ProjectUpdateCommand,
    build_project_management_projects_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogMetricViewModel,
    ProjectCatalogOverviewViewModel,
    ProjectCatalogWorkspaceViewModel,
    ProjectDetailFieldViewModel,
    ProjectDetailViewModel,
    ProjectRecordViewModel,
    ProjectStatusOptionViewModel,
)


class ProjectProjectsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementProjectsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_projects_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        status_filter: str = "all",
        selected_project_id: str | None = None,
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
                for project in filtered_projects
            ),
            selected_project_id=resolved_selected_project_id,
            selected_project_detail=self._build_detail_view_model(selected_project),
            empty_state=self._build_empty_state(
                all_projects=all_projects,
                filtered_projects=filtered_projects,
                search_text=normalized_search,
                status_filter=normalized_status_filter,
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


__all__ = ["ProjectProjectsWorkspacePresenter"]
