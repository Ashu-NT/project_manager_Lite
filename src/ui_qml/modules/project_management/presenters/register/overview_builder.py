from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.register import RegisterOverviewViewModel

from .filtering import matches_project
from .register_builder import build_register_overview
from .risk_builder import build_risk_overview
from .utils import WorkspaceMode


def build_overview(
    *,
    all_entries,
    filtered_entries,
    project_id: str,
    workspace_mode: WorkspaceMode,
) -> RegisterOverviewViewModel:
    scope_entries = tuple(entry for entry in all_entries if matches_project(entry, project_id))
    if workspace_mode == "risk":
        return build_risk_overview(scope_entries=scope_entries, filtered_entries=filtered_entries)
    return build_register_overview(scope_entries=scope_entries, filtered_entries=filtered_entries)
