from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Literal

from src.core.modules.project_management.api.desktop import (
    ProjectManagementRegisterDesktopApi,
    RegisterEntryCreateCommand,
    RegisterEntryUpdateCommand,
    build_project_management_register_desktop_api,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)
from src.ui_qml.modules.project_management.view_models.register import (
    RegisterCollectionViewModel,
    RegisterDetailFieldViewModel,
    RegisterDetailViewModel,
    RegisterMetricViewModel,
    RegisterOverviewViewModel,
    RegisterRecordViewModel,
    RegisterSelectorOptionViewModel,
    RegisterWorkspaceViewModel,
)

WorkspaceMode = Literal["risk", "register"]

_ACTIVE_STATUSES = {
    RegisterEntryStatus.OPEN,
    RegisterEntryStatus.IN_PROGRESS,
    RegisterEntryStatus.MITIGATED,
}


class ProjectRegisterWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementRegisterDesktopApi | None = None,
        workspace_mode: WorkspaceMode = "register",
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_register_desktop_api()
        self._workspace_mode = workspace_mode

    def build_workspace_state(
        self,
        *,
        project_id: str = "all",
        type_filter: str = "all",
        status_filter: str = "all",
        severity_filter: str = "all",
        search_text: str = "",
        selected_entry_id: str | None = None,
    ) -> RegisterWorkspaceViewModel:
        all_entries = self._desktop_api.list_entries()
        project_options = (
            RegisterSelectorOptionViewModel(value="all", label="All projects"),
            *(
                RegisterSelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in self._desktop_api.list_projects()
            ),
        )
        type_options = self._build_type_options()
        status_options = (
            RegisterSelectorOptionViewModel(value="all", label="All statuses"),
            *(
                RegisterSelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in self._desktop_api.list_statuses()
            ),
        )
        severity_options = (
            RegisterSelectorOptionViewModel(value="all", label="All severities"),
            *(
                RegisterSelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in self._desktop_api.list_severities()
            ),
        )
        normalized_project_id = self._normalize_filter(
            project_id,
            project_options,
            default_value="all",
        )
        normalized_type_filter = self._normalize_type_filter(
            type_filter,
            type_options,
        )
        normalized_status_filter = self._normalize_filter(
            status_filter,
            status_options,
            default_value="all",
        )
        normalized_severity_filter = self._normalize_filter(
            severity_filter,
            severity_options,
            default_value="all",
        )
        normalized_search = (search_text or "").strip()
        filtered_entries = tuple(
            entry
            for entry in all_entries
            if self._matches_project(entry, normalized_project_id)
            and self._matches_type(entry, normalized_type_filter)
            and self._matches_status(entry, normalized_status_filter)
            and self._matches_severity(entry, normalized_severity_filter)
            and self._matches_search(entry, normalized_search)
        )
        resolved_selected_entry_id = self._resolve_selected_entry_id(
            selected_entry_id,
            filtered_entries,
        )
        selected_entry = next(
            (
                entry
                for entry in filtered_entries
                if entry.id == resolved_selected_entry_id
            ),
            None,
        )
        return RegisterWorkspaceViewModel(
            overview=self._build_overview(
                all_entries=all_entries,
                filtered_entries=filtered_entries,
                project_id=normalized_project_id,
            ),
            project_options=project_options,
            type_options=type_options,
            status_options=status_options,
            severity_options=severity_options,
            selected_project_id=normalized_project_id,
            selected_type_filter=normalized_type_filter,
            selected_status_filter=normalized_status_filter,
            selected_severity_filter=normalized_severity_filter,
            search_text=normalized_search,
            entries=RegisterCollectionViewModel(
                title=self._entries_title(),
                subtitle=self._entries_subtitle(),
                empty_state=self._build_empty_state(
                    all_entries=all_entries,
                    filtered_entries=filtered_entries,
                    project_id=normalized_project_id,
                    type_filter=normalized_type_filter,
                    status_filter=normalized_status_filter,
                    severity_filter=normalized_severity_filter,
                    search_text=normalized_search,
                ),
                items=tuple(
                    self._to_record_view_model(entry)
                    for entry in filtered_entries
                ),
            ),
            selected_entry_id=resolved_selected_entry_id,
            selected_entry_detail=self._build_detail_view_model(selected_entry),
            urgent_entries=self._build_urgent_collection(filtered_entries),
            empty_state=self._build_empty_state(
                all_entries=all_entries,
                filtered_entries=filtered_entries,
                project_id=normalized_project_id,
                type_filter=normalized_type_filter,
                status_filter=normalized_status_filter,
                severity_filter=normalized_severity_filter,
                search_text=normalized_search,
            ),
        )

    def create_entry(self, payload: dict[str, Any]) -> None:
        command = RegisterEntryCreateCommand(
            project_id=self._require_text(
                payload,
                "projectId",
                "Choose a project before creating a register entry.",
            ),
            entry_type=self._resolve_entry_type(payload),
            title=self._require_text(payload, "title", "Register title is required."),
            description=self._optional_text(payload, "description") or "",
            severity=self._optional_text(payload, "severity") or RegisterEntrySeverity.MEDIUM.value,
            status=self._optional_text(payload, "status") or RegisterEntryStatus.OPEN.value,
            owner_name=self._optional_text(payload, "ownerName"),
            due_date=self._optional_date(payload, "dueDate"),
            impact_summary=self._optional_text(payload, "impactSummary") or "",
            response_plan=self._optional_text(payload, "responsePlan") or "",
        )
        self._desktop_api.create_entry(command)

    def update_entry(self, payload: dict[str, Any]) -> None:
        command = RegisterEntryUpdateCommand(
            entry_id=self._require_text(
                payload,
                "entryId",
                "Register entry ID is required for updates.",
            ),
            project_id=self._require_text(
                payload,
                "projectId",
                "Choose a project before saving this register entry.",
            ),
            entry_type=self._resolve_entry_type(payload),
            title=self._require_text(payload, "title", "Register title is required."),
            description=self._optional_text(payload, "description") or "",
            severity=self._optional_text(payload, "severity") or RegisterEntrySeverity.MEDIUM.value,
            status=self._optional_text(payload, "status") or RegisterEntryStatus.OPEN.value,
            owner_name=self._optional_text(payload, "ownerName"),
            due_date=self._optional_date(payload, "dueDate"),
            impact_summary=self._optional_text(payload, "impactSummary") or "",
            response_plan=self._optional_text(payload, "responsePlan") or "",
            expected_version=self._optional_int(payload, "expectedVersion"),
        )
        self._desktop_api.update_entry(command)

    def delete_entry(self, entry_id: str) -> None:
        normalized_entry_id = (entry_id or "").strip()
        if not normalized_entry_id:
            raise ValueError("Register entry ID is required to delete an entry.")
        self._desktop_api.delete_entry(normalized_entry_id)

    def _build_type_options(self) -> tuple[RegisterSelectorOptionViewModel, ...]:
        if self._workspace_mode == "risk":
            return (
                RegisterSelectorOptionViewModel(
                    value=RegisterEntryType.RISK.value,
                    label="Risk",
                ),
            )
        return (
            RegisterSelectorOptionViewModel(value="all", label="All entry types"),
            *(
                RegisterSelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in self._desktop_api.list_entry_types()
            ),
        )

    def _build_overview(
        self,
        *,
        all_entries,
        filtered_entries,
        project_id: str,
    ) -> RegisterOverviewViewModel:
        scope_entries = tuple(
            entry for entry in all_entries if self._matches_project(entry, project_id)
        )
        if self._workspace_mode == "risk":
            risk_entries = tuple(
                entry for entry in scope_entries if entry.entry_type == RegisterEntryType.RISK.value
            )
            visible_risks = tuple(
                entry for entry in filtered_entries if entry.entry_type == RegisterEntryType.RISK.value
            )
            today = date.today()
            due_soon_date = today + timedelta(days=7)
            return RegisterOverviewViewModel(
                title="Risk",
                subtitle="Project risk watchlist, mitigation ownership, and review focus.",
                metrics=(
                    RegisterMetricViewModel(
                        label="Visible risks",
                        value=str(len(visible_risks)),
                        supporting_text=f"{len(risk_entries)} total within the selected project scope.",
                    ),
                    RegisterMetricViewModel(
                        label="Active",
                        value=str(sum(1 for entry in visible_risks if self._is_active(entry.status))),
                        supporting_text="Open or in-flight risks that still need attention.",
                    ),
                    RegisterMetricViewModel(
                        label="Critical",
                        value=str(
                            sum(
                                1
                                for entry in visible_risks
                                if entry.severity == RegisterEntrySeverity.CRITICAL.value
                            )
                        ),
                        supporting_text="Highest-severity delivery risks in the current filter.",
                    ),
                    RegisterMetricViewModel(
                        label="Overdue",
                        value=str(sum(1 for entry in visible_risks if entry.is_overdue)),
                        supporting_text="Active risks with due dates already missed.",
                    ),
                    RegisterMetricViewModel(
                        label="Due soon",
                        value=str(
                            sum(
                                1
                                for entry in visible_risks
                                if entry.due_date is not None
                                and today <= entry.due_date <= due_soon_date
                                and self._is_active(entry.status)
                            )
                        ),
                        supporting_text="Active risks due in the next seven days.",
                    ),
                ),
            )
        return RegisterOverviewViewModel(
            title="Register",
            subtitle="Cross-project risks, issues, changes, and governance review queue.",
            metrics=(
                RegisterMetricViewModel(
                    label="Visible entries",
                    value=str(len(filtered_entries)),
                    supporting_text=f"{len(scope_entries)} total within the selected project scope.",
                ),
                RegisterMetricViewModel(
                    label="Open risks",
                    value=str(
                        sum(
                            1
                            for entry in filtered_entries
                            if entry.entry_type == RegisterEntryType.RISK.value
                            and self._is_active(entry.status)
                        )
                    ),
                    supporting_text="Risk records still open or under mitigation.",
                ),
                RegisterMetricViewModel(
                    label="Open issues",
                    value=str(
                        sum(
                            1
                            for entry in filtered_entries
                            if entry.entry_type == RegisterEntryType.ISSUE.value
                            and self._is_active(entry.status)
                        )
                    ),
                    supporting_text="Execution blockers needing ownership.",
                ),
                RegisterMetricViewModel(
                    label="Pending changes",
                    value=str(
                        sum(
                            1
                            for entry in filtered_entries
                            if entry.entry_type == RegisterEntryType.CHANGE.value
                            and entry.status in {
                                RegisterEntryStatus.OPEN.value,
                                RegisterEntryStatus.IN_PROGRESS.value,
                            }
                        )
                    ),
                    supporting_text="Changes awaiting decision or completion.",
                ),
                RegisterMetricViewModel(
                    label="Overdue",
                    value=str(sum(1 for entry in filtered_entries if entry.is_overdue)),
                    supporting_text="Active entries with missed due dates.",
                ),
            ),
        )

    def _build_urgent_collection(self, filtered_entries) -> RegisterCollectionViewModel:
        urgent_entries = tuple(
            self._to_record_view_model(entry)
            for entry in self._urgent_entries(filtered_entries)[:5]
        )
        return RegisterCollectionViewModel(
            title="Urgent Review Queue",
            subtitle="Severity-first shortlist to help triage what needs attention next.",
            empty_state=(
                "No urgent entries match the current filters."
                if filtered_entries
                else "No urgent entries are available for the current scope."
            ),
            items=urgent_entries,
        )

    def _build_detail_view_model(self, entry) -> RegisterDetailViewModel:
        if entry is None:
            return RegisterDetailViewModel(
                title="No entry selected",
                empty_state=(
                    "Select a risk entry to review mitigation details."
                    if self._workspace_mode == "risk"
                    else "Select a register entry to review governance details."
                ),
            )
        state = self._build_entry_state(entry)
        subtitle_values = [
            state["projectName"],
            state["typeLabel"],
            state["statusLabel"],
        ]
        return RegisterDetailViewModel(
            id=entry.id,
            title=entry.title,
            status_label=entry.severity_label,
            subtitle=" | ".join(value for value in subtitle_values if value),
            description=entry.description or "No description has been captured yet.",
            fields=(
                RegisterDetailFieldViewModel(
                    label="Owner",
                    value=entry.owner_name or "Unassigned",
                ),
                RegisterDetailFieldViewModel(
                    label="Due date",
                    value=entry.due_date_label,
                    supporting_text=(
                        "Entry is overdue."
                        if entry.is_overdue
                        else "No escalation due date has been set."
                        if entry.due_date is None
                        else ""
                    ),
                ),
                RegisterDetailFieldViewModel(
                    label="Impact",
                    value=entry.impact_summary or "No impact summary recorded.",
                ),
                RegisterDetailFieldViewModel(
                    label="Response plan",
                    value=entry.response_plan or "No response plan recorded.",
                ),
                RegisterDetailFieldViewModel(
                    label="Version",
                    value=str(entry.version),
                ),
            ),
            state=state,
        )

    def _to_record_view_model(self, entry) -> RegisterRecordViewModel:
        state = self._build_entry_state(entry)
        subtitle_parts = [
            state["typeLabel"],
            state["statusLabel"],
            state["ownerName"] or "Unassigned",
        ]
        supporting_parts = [
            f"Project: {state['projectName']}",
            f"Due: {state['dueDateLabel']}",
        ]
        if self._workspace_mode == "risk":
            subtitle_parts = [
                state["statusLabel"],
                state["ownerName"] or "Unassigned",
            ]
        return RegisterRecordViewModel(
            id=entry.id,
            title=entry.title,
            status_label=entry.severity_label,
            subtitle=" | ".join(part for part in subtitle_parts if part),
            supporting_text=" | ".join(part for part in supporting_parts if part),
            meta_text=self._preview_text(
                entry.response_plan,
                entry.impact_summary,
                entry.description,
            ),
            state=state,
        )

    @staticmethod
    def _build_entry_state(entry) -> dict[str, object]:
        return {
            "entryId": entry.id,
            "projectId": entry.project_id,
            "projectName": entry.project_name,
            "type": entry.entry_type,
            "typeLabel": entry.entry_type_label,
            "title": entry.title,
            "description": entry.description or "",
            "severity": entry.severity,
            "severityLabel": entry.severity_label,
            "status": entry.status,
            "statusLabel": entry.status_label,
            "ownerName": entry.owner_name or "",
            "dueDate": entry.due_date.isoformat() if entry.due_date else "",
            "dueDateLabel": entry.due_date_label,
            "impactSummary": entry.impact_summary or "",
            "responsePlan": entry.response_plan or "",
            "isOverdue": entry.is_overdue,
            "version": entry.version,
        }

    def _entries_title(self) -> str:
        return "Risk Register" if self._workspace_mode == "risk" else "Project Register"

    def _entries_subtitle(self) -> str:
        if self._workspace_mode == "risk":
            return "Track delivery risks, mitigation owners, and due-date pressure."
        return "Track risks, issues, and changes across the selected project scope."

    def _resolve_entry_type(self, payload: dict[str, Any]) -> str:
        if self._workspace_mode == "risk":
            return RegisterEntryType.RISK.value
        return self._optional_text(payload, "entryType") or RegisterEntryType.RISK.value

    def _normalize_type_filter(
        self,
        type_filter: str,
        type_options,
    ) -> str:
        if self._workspace_mode == "risk":
            return RegisterEntryType.RISK.value
        return self._normalize_filter(type_filter, type_options, default_value="all")

    @staticmethod
    def _normalize_filter(
        value: str,
        options,
        *,
        default_value: str,
    ) -> str:
        normalized_value = (value or default_value).strip().lower()
        available_values = {
            str(option.value or "").strip().lower(): option.value
            for option in options
        }
        return available_values.get(normalized_value, default_value)

    @staticmethod
    def _resolve_selected_entry_id(selected_entry_id: str | None, filtered_entries) -> str:
        normalized_id = (selected_entry_id or "").strip()
        if normalized_id and any(entry.id == normalized_id for entry in filtered_entries):
            return normalized_id
        if filtered_entries:
            return filtered_entries[0].id
        return ""

    @staticmethod
    def _matches_project(entry, project_id: str) -> bool:
        return project_id == "all" or entry.project_id == project_id

    @staticmethod
    def _matches_type(entry, type_filter: str) -> bool:
        return type_filter == "all" or entry.entry_type == type_filter

    @staticmethod
    def _matches_status(entry, status_filter: str) -> bool:
        return status_filter == "all" or entry.status == status_filter

    @staticmethod
    def _matches_severity(entry, severity_filter: str) -> bool:
        return severity_filter == "all" or entry.severity == severity_filter

    @staticmethod
    def _matches_search(entry, search_text: str) -> bool:
        if not search_text:
            return True
        normalized_search = search_text.casefold()
        haystacks = (
            entry.title or "",
            entry.project_name or "",
            entry.description or "",
            entry.owner_name or "",
            entry.impact_summary or "",
            entry.response_plan or "",
            entry.entry_type_label or "",
            entry.status_label or "",
            entry.severity_label or "",
        )
        return any(normalized_search in value.casefold() for value in haystacks)

    @staticmethod
    def _preview_text(*values: str | None) -> str:
        for value in values:
            normalized = " ".join((value or "").strip().split())
            if normalized:
                return normalized
        return "No additional notes recorded."

    @staticmethod
    def _is_active(status: str | RegisterEntryStatus) -> bool:
        return as_register_entry_status(status) in _ACTIVE_STATUSES

    def _urgent_entries(self, filtered_entries) -> list[object]:
        def sort_key(entry) -> tuple[int, int, date, str]:
            severity_order = {
                RegisterEntrySeverity.CRITICAL.value: 0,
                RegisterEntrySeverity.HIGH.value: 1,
                RegisterEntrySeverity.MEDIUM.value: 2,
                RegisterEntrySeverity.LOW.value: 3,
            }
            due_date = entry.due_date or date.max
            return (
                severity_order.get(entry.severity, 99),
                0 if entry.is_overdue else 1,
                due_date,
                (entry.title or "").casefold(),
            )

        return sorted(
            [
                entry
                for entry in filtered_entries
                if self._is_active(entry.status)
            ],
            key=sort_key,
        )

    def _build_empty_state(
        self,
        *,
        all_entries,
        filtered_entries,
        project_id: str,
        type_filter: str,
        status_filter: str,
        severity_filter: str,
        search_text: str,
    ) -> str:
        if filtered_entries:
            return ""
        if not all_entries:
            return (
                "No risks are available yet. Add the first project risk to start tracking mitigation."
                if self._workspace_mode == "risk"
                else "No register entries are available yet. Add the first risk, issue, or change to start tracking governance decisions."
            )
        if (
            project_id != "all"
            or type_filter != ("RISK" if self._workspace_mode == "risk" else "all")
            or status_filter != "all"
            or severity_filter != "all"
            or search_text
        ):
            return (
                "No risks match the current filters."
                if self._workspace_mode == "risk"
                else "No register entries match the current filters."
            )
        return (
            "No risks are available yet."
            if self._workspace_mode == "risk"
            else "No register entries are available yet."
        )

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
            raise ValueError("Due date must use YYYY-MM-DD.") from exc


__all__ = ["ProjectRegisterWorkspacePresenter"]
