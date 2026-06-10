from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
)
from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
    TaskSelectorOptionViewModel,
)

from .collaboration_mapper import (
    to_collaboration_comment_record_view_model,
    to_collaboration_presence_record_view_model,
)
from .overview_builder import build_empty_overview


def build_collaboration_comments_collection(
    *,
    selected_task,
    snapshot,
) -> CollaborationCollectionViewModel:
    if selected_task is None:
        return CollaborationCollectionViewModel(
            title="Task Collaboration",
            subtitle=(
                "Comments, mentions, attachments, and linked shared documents "
                "for the selected task."
            ),
            empty_state=(
                "Select a task to review collaboration updates and post comments."
            ),
        )
    if snapshot is None or not snapshot.comments:
        return CollaborationCollectionViewModel(
            title="Task Collaboration",
            subtitle=(
                "Comments, mentions, attachments, and linked shared documents "
                "for the selected task."
            ),
            empty_state=(
                "No collaboration updates are linked to the selected task yet."
            ),
        )
    return CollaborationCollectionViewModel(
        title="Task Collaboration",
        subtitle=(
            "Comments, mentions, attachments, and linked shared documents "
            "for the selected task."
        ),
        items=tuple(
            to_collaboration_comment_record_view_model(comment)
            for comment in snapshot.comments
        ),
        empty_state="",
    )


def build_collaboration_presence_collection(
    *,
    selected_task,
    snapshot,
) -> CollaborationCollectionViewModel:
    if selected_task is None:
        return CollaborationCollectionViewModel(
            title="Active Presence",
            subtitle="People currently reviewing or updating the selected task.",
            empty_state="Select a task to review active collaboration presence.",
        )
    if snapshot is None or not snapshot.active_presence:
        return CollaborationCollectionViewModel(
            title="Active Presence",
            subtitle="People currently reviewing or updating the selected task.",
            empty_state=(
                "No active collaborators are visible for the selected task right now."
            ),
        )
    return CollaborationCollectionViewModel(
        title="Active Presence",
        subtitle="People currently reviewing or updating the selected task.",
        items=tuple(
            to_collaboration_presence_record_view_model(item)
            for item in snapshot.active_presence
        ),
        empty_state="",
    )


def build_task_collaboration_state(
    desktop_api,
    collaboration_desktop_api,
    *,
    task_id: str,
) -> TaskCatalogWorkspaceViewModel:
    normalized_task_id = (task_id or "").strip()
    selected_task = (
        desktop_api.get_task(normalized_task_id) if normalized_task_id else None
    )
    collaboration_snapshot = (
        collaboration_desktop_api.build_task_snapshot(normalized_task_id)
        if normalized_task_id
        else None
    )
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_task_id=normalized_task_id if selected_task is not None else "",
        collaboration_mention_options=tuple(
            TaskSelectorOptionViewModel(value=option.value, label=option.label)
            for option in (
                collaboration_snapshot.mention_options
                if collaboration_snapshot is not None
                else ()
            )
        ),
        collaboration_document_options=tuple(
            TaskSelectorOptionViewModel(value=option.value, label=option.label)
            for option in (
                collaboration_snapshot.document_options
                if collaboration_snapshot is not None
                else ()
            )
        ),
        collaboration_comments=build_collaboration_comments_collection(
            selected_task=selected_task,
            snapshot=collaboration_snapshot,
        ),
        collaboration_presence=build_collaboration_presence_collection(
            selected_task=selected_task,
            snapshot=collaboration_snapshot,
        ),
    )
