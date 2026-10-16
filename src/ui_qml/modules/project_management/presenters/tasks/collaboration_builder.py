from __future__ import annotations

from src.ui_qml.modules.project_management.presenters.collaboration.formatting import (
    format_document_option_label,
)
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
            total_count=snapshot.comment_total if snapshot is not None else 0,
            page=snapshot.comment_page if snapshot is not None else 1,
            page_size=snapshot.comment_page_size if snapshot is not None else 25,
        )
    return CollaborationCollectionViewModel(
        title="Task Collaboration",
        subtitle=(
            "Comments, mentions, attachments, and linked shared documents "
            "for the selected task."
        ),
        items=tuple(
            to_collaboration_comment_record_view_model(
                comment,
                linked_documents=snapshot.linked_documents.get(comment.id, ()),
                principal_user_id=snapshot.action_context.principal_user_id,
                can_manage=snapshot.action_context.can_manage,
                can_read=snapshot.action_context.can_read,
            )
            for comment in snapshot.comments
        ),
        empty_state="",
        total_count=snapshot.comment_total,
        page=snapshot.comment_page,
        page_size=snapshot.comment_page_size,
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
    page: int = 1,
    page_size: int = 25,
) -> TaskCatalogWorkspaceViewModel:
    normalized_task_id = (task_id or "").strip()
    selected_task = (
        desktop_api.get_task(normalized_task_id) if normalized_task_id else None
    )
    collaboration_snapshot = (
        collaboration_desktop_api.build_task_snapshot(
            normalized_task_id, page=page, page_size=page_size
        )
        if normalized_task_id
        else None
    )
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_task_id=normalized_task_id if selected_task is not None else "",
        collaboration_mention_options=(
            (
                TaskSelectorOptionViewModel(
                    value="everyone",
                    label="@everyone  Mention everyone with access to this task",
                ),
            )
            if collaboration_snapshot is not None and collaboration_snapshot.available
            else ()
        )
        + tuple(
            TaskSelectorOptionViewModel(value=option.handle, label=option.label)
            for option in (
                collaboration_snapshot.mention_candidates
                if collaboration_snapshot is not None
                else ()
            )
        ),
        collaboration_document_options=tuple(
            TaskSelectorOptionViewModel(
                value=option.id, label=format_document_option_label(option)
            )
            for option in (
                collaboration_snapshot.documents
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
