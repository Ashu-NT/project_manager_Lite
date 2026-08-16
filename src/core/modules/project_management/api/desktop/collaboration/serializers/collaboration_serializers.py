"""Domain-to-DTO serializers for collaboration entities."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.collaboration.models.collaboration_models import (
    CollaborationInboxDesktopDto,
    CollaborationPresenceDesktopDto,
    TaskCollaborationCommentDesktopDto,
    TaskCollaborationReactionSummaryDto,
)
from src.core.modules.project_management.api.desktop.collaboration.utils.formatting import (
    format_datetime,
    format_enum_label,
    format_linked_document_label,
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


def serialize_task_comment(
    comment,
    *,
    linked_documents,
    principal_user_id: str = "",
    can_manage: bool = False,
    can_read: bool = False,
    parent_author_username: str = "",
    thread_depth: int = 0,
    reply_count: int = 0,
) -> TaskCollaborationCommentDesktopDto:
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
    is_deleted = bool(getattr(comment, "deleted_at", None))
    updated_at = getattr(comment, "updated_at", None)
    reactions_map = getattr(comment, "reactions", None) or {}
    reactions = tuple(
        TaskCollaborationReactionSummaryDto(
            emoji=emoji,
            count=len(user_ids),
            reactor_user_ids=tuple(user_ids),
            reacted_by_current_user=bool(
                principal_user_id and principal_user_id in user_ids
            ),
        )
        for emoji, user_ids in sorted(reactions_map.items())
        if user_ids
    )
    reactions_label = (
        "  ".join(f"{reaction.emoji} {reaction.count}" for reaction in reactions)
        if reactions
        else ""
    )
    return TaskCollaborationCommentDesktopDto(
        comment_id=comment.id,
        task_id=comment.task_id,
        author_username=(comment.author_username or "unknown").strip() or "unknown",
        body="This comment was deleted." if is_deleted else comment.body,
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
        author_user_id=getattr(comment, "author_user_id", None),
        parent_comment_id=getattr(comment, "parent_comment_id", None),
        is_reply=bool(getattr(comment, "parent_comment_id", None)),
        updated_at=updated_at,
        updated_at_label=format_datetime(updated_at) if updated_at else "",
        is_edited=bool(updated_at) and not is_deleted,
        is_deleted=is_deleted,
        reactions=reactions,
        reactions_label=reactions_label,
        parent_author_username=parent_author_username,
        thread_depth=max(int(thread_depth), 0),
        reply_count=max(int(reply_count), 0),
        can_reply=bool(can_manage and not is_deleted),
        can_edit=bool(
            can_manage
            and not is_deleted
            and principal_user_id
            and principal_user_id == getattr(comment, "author_user_id", None)
        ),
        can_delete=bool(can_manage and not is_deleted),
        can_react=bool(can_read and principal_user_id and not is_deleted),
        revision=int(getattr(comment, "version", 1) or 1),
        deletion_reason=str(getattr(comment, "deletion_reason", "") or ""),
    )


__all__ = [
    "serialize_inbox_item",
    "serialize_presence_item",
    "serialize_task_comment",
]
