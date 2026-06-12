from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_collaboration_detail_view_model,
)
from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationDetailFieldViewModel,
    CollaborationDetailViewModel,
    CollaborationRecordViewModel,
)

from .utils import panel_label


def to_record_view_model(item: dict[str, object]) -> CollaborationRecordViewModel:
    state = dict(item.get("state") or {})
    return CollaborationRecordViewModel(
        id=str(item.get("id") or ""),
        title=str(item.get("title") or ""),
        status_label=str(item.get("statusLabel") or ""),
        subtitle=str(item.get("subtitle") or ""),
        supporting_text=str(item.get("supportingText") or ""),
        meta_text=str(item.get("metaText") or ""),
        state=state,
    )


def matching_items_for_task_or_project(
    *,
    panel_item_index: dict[str, dict[str, dict[str, object]]],
    source_panels: tuple[str, ...],
    task_id: str,
    project_id: str,
    exclude_item_id: str,
) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for pid in source_panels:
        for item in panel_item_index.get(pid, {}).values():
            if str(item.get("id") or "") == exclude_item_id:
                continue
            state = dict(item.get("state") or {})
            same_task = task_id and str(state.get("taskId") or "") == task_id
            same_project = project_id and str(state.get("projectId") or "") == project_id
            if not same_task and not same_project:
                continue
            item_id = str(item.get("id") or "")
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            matches.append(dict(item))
    matches.sort(
        key=lambda e: str(dict(e.get("state") or {}).get("createdAt") or ""),
        reverse=True,
    )
    return matches[:10]


def build_detail_payload(
    panel_id: str,
    item: dict[str, object],
    panel_item_index: dict[str, dict[str, dict[str, object]]],
) -> dict[str, object]:
    state = dict(item.get("state") or {})
    project_id = str(state.get("projectId") or "")
    task_id = str(state.get("taskId") or "")
    item_id = str(item.get("id") or "")
    route_id = str(state.get("routeId") or "")

    related: list[dict[str, object]] = []
    if route_id:
        related.append({
            "id": f"{item_id}:source",
            "title": "Open Source Workspace",
            "statusLabel": "Navigation",
            "subtitle": route_id.replace(".", " / "),
            "supportingText": str(item.get("subtitle") or ""),
            "metaText": str(item.get("metaText") or ""),
            "state": {"routeId": route_id},
        })
    if task_id:
        related.append({
            "id": f"{item_id}:task",
            "title": "Related Task",
            "statusLabel": "Task",
            "subtitle": task_id,
            "supportingText": str(item.get("title") or ""),
            "metaText": "",
            "state": {"routeId": "project_management.tasks", "taskId": task_id},
        })
    if project_id:
        related.append({
            "id": f"{item_id}:project",
            "title": "Related Project",
            "statusLabel": "Project",
            "subtitle": project_id,
            "supportingText": str(state.get("projectName") or ""),
            "metaText": "",
            "state": {
                "routeId": "project_management.projects",
                "projectId": project_id,
            },
        })

    activity_items = matching_items_for_task_or_project(
        panel_item_index=panel_item_index,
        source_panels=("activity", "team_updates"),
        task_id=task_id,
        project_id=project_id,
        exclude_item_id=item_id,
    )
    audit_items = matching_items_for_task_or_project(
        panel_item_index=panel_item_index,
        source_panels=("audit", "inbox", "mentions", "approvals"),
        task_id=task_id,
        project_id=project_id,
        exclude_item_id=item_id,
    )

    detail = CollaborationDetailViewModel(
        id=item_id,
        title=str(item.get("title") or ""),
        status_label=str(item.get("statusLabel") or ""),
        subtitle=str(item.get("subtitle") or ""),
        description=str(item.get("supportingText") or ""),
        state={
            "panelId": panel_id,
            "routeId": route_id,
            **state,
        },
        fields=(
            CollaborationDetailFieldViewModel("Panel", panel_label(panel_id)),
            CollaborationDetailFieldViewModel(
                "Project",
                str(state.get("projectName") or state.get("projectId") or "Cross-project"),
            ),
            CollaborationDetailFieldViewModel(
                "Actor",
                str(
                    state.get("actorUsername")
                    or state.get("requestor")
                    or state.get("username")
                    or "System"
                ),
            ),
            CollaborationDetailFieldViewModel(
                "Created",
                str(item.get("metaText") or state.get("createdAt") or "Timestamp unavailable"),
            ),
            CollaborationDetailFieldViewModel(
                "Source",
                str(route_id or "No linked source route"),
            ),
        ),
        activity=CollaborationCollectionViewModel(
            title="Activity",
            subtitle="Related workflow and collaboration events.",
            empty_state="No related activity is available for this collaboration item.",
            items=tuple(to_record_view_model(e) for e in activity_items),
        ),
        related_items=CollaborationCollectionViewModel(
            title="Related Items",
            subtitle="Open the source workspace or review related project records.",
            empty_state="No related drill-down targets are available for this item.",
            items=tuple(to_record_view_model(e) for e in related),
        ),
        audit=CollaborationCollectionViewModel(
            title="Audit",
            subtitle="Related workflow trace and governance trail.",
            empty_state="No related audit events were found for this item.",
            items=tuple(to_record_view_model(e) for e in audit_items),
        ),
    )
    return serialize_collaboration_detail_view_model(detail)


__all__ = ["build_detail_payload", "matching_items_for_task_or_project", "to_record_view_model"]
