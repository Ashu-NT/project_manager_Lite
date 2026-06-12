from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationRecordViewModel,
)


def to_collaboration_comment_record_view_model(comment) -> CollaborationRecordViewModel:
    meta_parts = [comment.created_at_label]
    if comment.mentions:
        meta_parts.append(f"Mentions: {comment.mentions_label}")
    if comment.linked_documents:
        meta_parts.append(f"Linked: {comment.linked_documents_label}")
    elif comment.attachments:
        meta_parts.append(f"Attachments: {comment.attachments_label}")
    return CollaborationRecordViewModel(
        id=comment.comment_id,
        title=f"@{comment.author_username}",
        status_label="Mentions" if comment.mentions else "Comment",
        subtitle=comment.body,
        supporting_text=(
            f"Attachments: {comment.attachments_label}"
            if comment.attachments
            else "No attachment references recorded."
        ),
        meta_text=" | ".join(part for part in meta_parts if part),
        state={
            "taskId": comment.task_id,
            "commentId": comment.comment_id,
            "mentions": list(comment.mentions),
            "attachments": list(comment.attachments),
            "linkedDocuments": list(comment.linked_documents),
        },
    )


def to_collaboration_presence_record_view_model(presence) -> CollaborationRecordViewModel:
    return CollaborationRecordViewModel(
        id=f"{presence.task_id}:{presence.username}",
        title=presence.who_label,
        status_label=presence.activity_label,
        subtitle=f"Last seen {presence.last_seen_at_label}",
        supporting_text=(
            "You are included in this presence view." if presence.is_self else ""
        ),
        meta_text=f"@{presence.username}" if presence.username else "",
        state={
            "taskId": presence.task_id,
            "username": presence.username,
            "isSelf": presence.is_self,
        },
    )
