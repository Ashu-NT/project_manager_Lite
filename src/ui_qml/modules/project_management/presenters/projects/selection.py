from __future__ import annotations

from typing import Any

def resolve_selected_project_id(
    selected_project_id: str | None,
    filtered_projects: Any,
) -> str:
    # Never silently reassign selection to an unrelated project. The
    # previous fallback picked filtered_projects[0] whenever the requested
    # id wasn't present on the current page -- meaning a plain page turn
    # or filter change (e.g. selecting a project on page 1, then paging to
    # page 2) silently swapped the selection to some other project the
    # user never clicked, with no explicit action from them. Selection
    # must only ever change through an explicit selectProject() call; a
    # refresh that can no longer see the previously selected row should
    # clear the selection, not substitute a different one.
    normalized_id = (selected_project_id or "").strip()
    if normalized_id and any(project.id == normalized_id for project in filtered_projects):
        return normalized_id
    return ""
