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
    normalize_filter,
    normalize_type_filter,
)
from .overview_builder import build_overview
from .selection import resolve_selected_entry_id
from .urgent_queue_builder import build_urgent_collection
from .workspace_mode import WorkspaceMode


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
    page: int = 1,
    page_size: int = 25,
    sort_key: str = "triage",
    sort_direction: str = "asc",
) -> RegisterWorkspaceViewModel:
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
    entry_page = desktop_api.list_entry_page(
        project_id=normalized_project_id,
        entry_type=normalized_type_filter,
        status=normalized_status_filter,
        severity=normalized_severity_filter,
        search_text=normalized_search,
        page=page,
        page_size=page_size,
        sort_key=sort_key,
        sort_direction=sort_direction,
    )
    resolved_selected_entry_id = resolve_selected_entry_id(selected_entry_id, entry_page.items)
    selected_entry = next(
        (entry for entry in entry_page.items if entry.id == resolved_selected_entry_id),
        None,
    )
    empty_state = build_empty_state(
        total=entry_page.scope_total,
        filtered_total=entry_page.filtered_total,
        project_id=normalized_project_id,
        type_filter=normalized_type_filter,
        status_filter=normalized_status_filter,
        severity_filter=normalized_severity_filter,
        search_text=normalized_search,
        workspace_mode=workspace_mode,
    )
    return RegisterWorkspaceViewModel(
        overview=build_overview(
            entry_page=entry_page,
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
                for entry in entry_page.items
            ),
        ),
        selected_entry_id=resolved_selected_entry_id,
        selected_entry_detail=build_detail_view_model(selected_entry, workspace_mode=workspace_mode),
        urgent_entries=build_urgent_collection(
            entry_page.urgent_items,
            filtered_total=entry_page.filtered_total,
            workspace_mode=workspace_mode,
        ),
        empty_state=empty_state,
        total_count=entry_page.filtered_total,
        page=entry_page.page,
        page_size=entry_page.page_size,
        sort_key=entry_page.sort_key,
        sort_direction=entry_page.sort_direction,
    )
