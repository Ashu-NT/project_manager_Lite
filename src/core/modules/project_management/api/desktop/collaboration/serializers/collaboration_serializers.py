"""Domain-to-DTO serializers for collaboration entities."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.collaboration.models.collaboration_models import (
    CollaborationInboxDesktopDto,
    CollaborationNotificationDesktopDto,
    CollaborationPresenceDesktopDto,
    TaskCollaborationCommentDesktopDto,
)
from src.core.modules.project_management.api.desktop.collaboration.utils.formatting import (
    format_datetime,
    format_enum_label,
    format_linked_document_label,
)


def serialize_notification(item) -> CollaborationNotificationDesktopDto:
    return CollaborationNotificationDesktopDto(
        entity_id=item.entity_id,
        notification_type=item.notification_type,
        notification_type_label=format_enum_label(item.notification_type),
        entity_type=item.entity_type,
        headline=item.headline,
        body_preview=item.body_preview,
        actor_username=item.actor_username,
        created_at=item.created_at,
        created_at_label=format_datetime(item.created_at),
        project_id=item.project_id,
        project_name=item.project_name or "",
        attention=bool(item.attention),
    )


def serialize_inbox_item(item) -> CollaborationInboxDesktopDto:
    mentions = tuple(str(m).strip() for m in item.mentions if str(m).strip())
    return CollaborationInboxDesktopDto(
        comment_id=item.comment_id,
        task_id=item.task_id,
        task_name=item.task_name,
        project_id=item.project_id,
        project_name=item.project_name,
        author_username=item.author_username,
        body_preview=item.body_preview,
        mentions=mentions,
        mentions_label=(
            ", ".join(f"@{m}" for m in mentions) if mentions else "No direct mentions"
        ),
        created_at=item.created_at,
        created_at_label=format_datetime(item.created_at),
        unread=bool(item.unread),
    )


def serialize_presence_item(item) -> CollaborationPresenceDesktopDto:
    display_name = (item.display_name or "").strip() or None
    username = (item.username or "").strip()
    if display_name and username:
        who_label = f"{display_name} (@{username})"
    elif display_name:
        who_label = display_name
    else:
        who_label = f"@{username}" if username else "Unknown"
    return CollaborationPresenceDesktopDto(
        task_id=item.task_id,
        task_name=item.task_name,
        project_id=item.project_id,
        project_name=item.project_name,
        username=username,
        display_name=display_name,
        activity=item.activity,
        activity_label=format_enum_label(item.activity),
        who_label=who_label,
        last_seen_at=item.last_seen_at,
        last_seen_at_label=format_datetime(item.last_seen_at),
        is_self=bool(item.is_self),
    )


def serialize_task_comment(comment, *, linked_documents) -> TaskCollaborationCommentDesktopDto:
    mentions = tuple(
        str(m).strip()
        for m in getattr(comment, "mentions", ())
        if str(m).strip()
    )
    attachments = tuple(
        str(a).strip()
        for a in getattr(comment, "attachments", ())
        if str(a).strip()
    )
    linked_document_labels = tuple(
        format_linked_document_label(document) for document in linked_documents
    )
    return TaskCollaborationCommentDesktopDto(
        comment_id=comment.id,
        task_id=comment.task_id,
        author_username=(comment.author_username or "unknown").strip() or "unknown",
        body=comment.body,
        mentions=mentions,
        mentions_label=(
            ", ".join(f"@{m}" for m in mentions) if mentions else "No direct mentions"
        ),
        attachments=attachments,
        attachments_label=", ".join(attachments) if attachments else "No attachments",
        linked_documents=linked_document_labels,
        linked_documents_label=(
            ", ".join(linked_document_labels)
            if linked_document_labels
            else "No linked documents"
        ),
        created_at=comment.created_at,
        created_at_label=format_datetime(comment.created_at),
    )


__all__ = [
    "serialize_inbox_item",
    "serialize_notification",
    "serialize_presence_item",
    "serialize_task_comment",
]
