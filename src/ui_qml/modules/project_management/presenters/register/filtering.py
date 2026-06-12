from __future__ import annotations

from typing import Any

from src.core.modules.project_management.domain.risk.register import RegisterEntryType

from .utils import WorkspaceMode

def matches_project(entry: Any, project_id: str) -> bool:
    return project_id == "all" or entry.project_id == project_id

def matches_type(entry: Any, type_filter: str) -> bool:
    return type_filter == "all" or entry.entry_type == type_filter

def matches_status(entry: Any, status_filter: str) -> bool:
    return status_filter == "all" or entry.status == status_filter

def matches_severity(entry: Any, severity_filter: str) -> bool:
    return severity_filter == "all" or entry.severity == severity_filter

def matches_search(entry: Any, search_text: str) -> bool:
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

def normalize_filter(value: str, options: Any, *, default_value: str) -> str:
    normalized_value = (value or default_value).strip().lower()
    available_values = {
        str(option.value or "").strip().lower(): option.value
        for option in options
    }
    return available_values.get(normalized_value, default_value)

def normalize_type_filter(
    type_filter: str,
    type_options: Any,
    *,
    workspace_mode: WorkspaceMode,
) -> str:
    if workspace_mode == "risk":
        return RegisterEntryType.RISK.value
    return normalize_filter(type_filter, type_options, default_value="all")

def build_empty_state(
    *,
    all_entries: Any,
    filtered_entries: Any,
    project_id: str,
    type_filter: str,
    status_filter: str,
    severity_filter: str,
    search_text: str,
    workspace_mode: WorkspaceMode,
) -> str:
    if filtered_entries:
        return ""
    if not all_entries:
        return (
            "No risks are available yet. Add the first project risk to start tracking mitigation."
            if workspace_mode == "risk"
            else "No register entries are available yet. Add the first risk, issue, or change to start tracking governance decisions."
        )
    if (
        project_id != "all"
        or type_filter != (RegisterEntryType.RISK.value if workspace_mode == "risk" else "all")
        or status_filter != "all"
        or severity_filter != "all"
        or search_text
    ):
        return (
            "No risks match the current filters."
            if workspace_mode == "risk"
            else "No register entries match the current filters."
        )
    return (
        "No risks are available yet."
        if workspace_mode == "risk"
        else "No register entries are available yet."
    )
