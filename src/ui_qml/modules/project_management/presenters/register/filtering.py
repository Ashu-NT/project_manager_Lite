from __future__ import annotations

from typing import Any

from src.core.modules.project_management.domain.risk.register import RegisterEntryType

from .utils import WorkspaceMode

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
    total: int,
    filtered_total: int,
    project_id: str,
    type_filter: str,
    status_filter: str,
    severity_filter: str,
    search_text: str,
    workspace_mode: WorkspaceMode,
) -> str:
    if filtered_total:
        return ""
    if not total:
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
