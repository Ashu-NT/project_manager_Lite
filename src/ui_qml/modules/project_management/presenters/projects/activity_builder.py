from __future__ import annotations

from src.core.platform.api.desktop.history.activity.activity import PlatformActivityDesktopApi
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogWorkspaceViewModel,
    ProjectRecordViewModel,
    ProjectSectionCollectionViewModel,
)

from .overview_builder import build_empty_overview

# Keyword classification kept local to this builder rather than imported from
# another module's presenter layer -- PM must not import Inventory/Procurement
# packages, and this is a small, self-contained rule, not a shared contract.
_SUCCESS_KEYWORDS = ("creat", "add", "open", "approv", "complet")
_DANGER_KEYWORDS = ("delet", "cancel", "reject", "close", "remov")
_WARNING_KEYWORDS = ("updat", "edit", "modif", "submit", "post", "transfer", "issue", "return", "adjust")


def _status_label_for_action(action: str) -> str:
    normalized = (action or "").lower()
    if any(keyword in normalized for keyword in _SUCCESS_KEYWORDS):
        return "Success"
    if any(keyword in normalized for keyword in _DANGER_KEYWORDS):
        return "Danger"
    if any(keyword in normalized for keyword in _WARNING_KEYWORDS):
        return "Warning"
    return ""


def build_project_activity_state(
    activity_api: PlatformActivityDesktopApi | None,
    *,
    project_id: str,
) -> ProjectCatalogWorkspaceViewModel:
    normalized_project_id = (project_id or "").strip()
    items: tuple[ProjectRecordViewModel, ...] = ()
    if activity_api is not None and normalized_project_id:
        result = activity_api.list_recent(
            entity_type="project",
            entity_id=normalized_project_id,
            limit=50,
        )
        if result.ok and result.data is not None:
            items = tuple(
                ProjectRecordViewModel(
                    id=entry.id,
                    title=entry.human_message or entry.action,
                    status_label=_status_label_for_action(entry.action),
                    subtitle="",
                    supporting_text="",
                    meta_text=entry.timestamp.strftime("%d %b %Y %H:%M") if entry.timestamp else "",
                )
                for entry in result.data
            )
    return ProjectCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=normalized_project_id,
        project_activity=ProjectSectionCollectionViewModel(
            title="Activity",
            subtitle=f"{len(items)} recent event(s) for this project." if items else "Recent project activity.",
            empty_state="No activity has been recorded for this project yet.",
            items=items,
        ),
    )
