from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementRegisterDesktopApi,
)
from src.core.modules.project_management.domain.risk.register import RegisterEntryType
from src.ui_qml.modules.project_management.view_models.register import (
    RegisterCollectionViewModel,
    RegisterSelectorOptionViewModel,
    RegisterWorkspaceViewModel,
)

from .detail_builder import build_detail_view_model
from .entry_mapper import to_record_view_model
from .filtering import (
    build_empty_state,
    matches_project,
    matches_search,
    matches_severity,
    matches_status,
    matches_type,
    normalize_filter,
    normalize_type_filter,
)
from .overview_builder import build_overview
from .selection import resolve_selected_entry_id
from .urgent_queue_builder import build_urgent_collection
from .utils import WorkspaceMode


def _build_type_options(
    desktop_api: ProjectManagementRegisterDesktopApi,
    *,
    workspace_mode: WorkspaceMode,
) -> tuple[RegisterSelectorOptionViewModel, ...]:
    if workspace_mode == "risk":
        return (
            RegisterSelectorOptionViewModel(
                value=RegisterEntryType.RISK.value,
                label="Risk",
            ),
        )
    return (
        RegisterSelectorOptionViewModel(value="all", label="All entry types"),
        *(
            RegisterSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_entry_types()
        ),
    )


def _entries_title(workspace_mode: WorkspaceMode) -> str:
    return "Risk Register" if workspace_mode == "risk" else "Project Register"


def _entries_subtitle(workspace_mode: WorkspaceMode) -> str:
    if workspace_mode == "risk":
        return "Track delivery risks, mitigation owners, and due-date pressure."
    return "Track risks, issues, and changes across the selected project scope."


def build_workspace_state(
    desktop_api: ProjectManagementRegisterDesktopApi,
    *,
    project_id: str = "all",
    type_filter: str = "all",
    status_filter: str = "all",
    severity_filter: str = "all",
    search_text: str = "",
    selected_entry_id: str | None = None,
    workspace_mode: WorkspaceMode = "register",
) -> RegisterWorkspaceViewModel:
    all_entries = desktop_api.list_entries()
    project_options = (
        RegisterSelectorOptionViewModel(value="all", label="All projects"),
        *(
            RegisterSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_projects()
        ),
    )
    type_options = _build_type_options(desktop_api, workspace_mode=workspace_mode)
    status_options = (
        RegisterSelectorOptionViewModel(value="all", label="All statuses"),
        *(
            RegisterSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_statuses()
        ),
    )
    severity_options = (
        RegisterSelectorOptionViewModel(value="all", label="All severities"),
        *(
            RegisterSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_severities()
        ),
    )
    normalized_project_id = normalize_filter(project_id, project_options, default_value="all")
    normalized_type_filter = normalize_type_filter(
        type_filter, type_options, workspace_mode=workspace_mode
    )
    normalized_status_filter = normalize_filter(status_filter, status_options, default_value="all")
    normalized_severity_filter = normalize_filter(
        severity_filter, severity_options, default_value="all"
    )
    normalized_search = (search_text or "").strip()
    filtered_entries = tuple(
        entry
        for entry in all_entries
        if matches_project(entry, normalized_project_id)
        and matches_type(entry, normalized_type_filter)
        and matches_status(entry, normalized_status_filter)
        and matches_severity(entry, normalized_severity_filter)
        and matches_search(entry, normalized_search)
    )
    resolved_selected_entry_id = resolve_selected_entry_id(selected_entry_id, filtered_entries)
    selected_entry = next(
        (entry for entry in filtered_entries if entry.id == resolved_selected_entry_id),
        None,
    )
    empty_state = build_empty_state(
        all_entries=all_entries,
        filtered_entries=filtered_entries,
        project_id=normalized_project_id,
        type_filter=normalized_type_filter,
        status_filter=normalized_status_filter,
        severity_filter=normalized_severity_filter,
        search_text=normalized_search,
        workspace_mode=workspace_mode,
    )
    return RegisterWorkspaceViewModel(
        overview=build_overview(
            all_entries=all_entries,
            filtered_entries=filtered_entries,
            project_id=normalized_project_id,
            workspace_mode=workspace_mode,
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
            title=_entries_title(workspace_mode),
            subtitle=_entries_subtitle(workspace_mode),
            empty_state=empty_state,
            items=tuple(
                to_record_view_model(entry, workspace_mode=workspace_mode)
                for entry in filtered_entries
            ),
        ),
        selected_entry_id=resolved_selected_entry_id,
        selected_entry_detail=build_detail_view_model(selected_entry, workspace_mode=workspace_mode),
        urgent_entries=build_urgent_collection(filtered_entries, workspace_mode=workspace_mode),
        empty_state=empty_state,
    )
