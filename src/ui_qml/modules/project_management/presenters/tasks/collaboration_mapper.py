from __future__ import annotations

from src.core.modules.project_management.application.collaboration.mappers.collaboration import (
    map_reactions,
)
from src.ui_qml.modules.project_management.presenters.collaboration.formatting import (
    format_linked_document_label,
)
from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationRecordViewModel,
)


def to_collaboration_comment_record_view_model(
    comment,
    *,
    linked_documents=(),
    principal_user_id="",
    can_manage=False,
    can_read=False,
) -> CollaborationRecordViewModel:
    deleted = bool(comment.deleted_at)
    mentions = (
        ()
        if deleted
        else tuple(
            str(value).strip() for value in comment.mentions if str(value).strip()
        )
    )
    attachments = (
        ()
        if deleted
        else tuple(
            str(value).strip() for value in comment.attachments if str(value).strip()
        )
    )
    documents = (
        ()
        if deleted
        else tuple(
            format_linked_document_label(document) for document in linked_documents
        )
    )
    mentions_label = (
        ", ".join(f"@{value}" for value in mentions) or "No direct mentions"
    )
    attachments_label = ", ".join(attachments) or "No attachments"
    documents_label = ", ".join(documents) or "No linked documents"
    updated_at = comment.updated_at
    edited = bool(updated_at) and not deleted
    raw_reactions = comment.reactions
    reactions = (
        ()
        if deleted
        else (
            map_reactions(dict(raw_reactions), principal_user_id=principal_user_id)
            if isinstance(raw_reactions, dict)
            or (raw_reactions and not hasattr(raw_reactions[0], "emoji"))
            else raw_reactions
        )
    )
    can_reply = bool(can_manage and not deleted)
    can_edit = bool(
        can_reply and principal_user_id and principal_user_id == comment.author_user_id
    )
    can_react = bool(can_read and principal_user_id and not deleted)
    meta_parts = [comment.created_at.strftime("%Y-%m-%d %H:%M")]
    if edited:
        meta_parts.append(f"Edited {updated_at.strftime('%Y-%m-%d %H:%M')}")
    if mentions:
        meta_parts.append(f"Mentions: {mentions_label}")
    if documents:
        meta_parts.append(f"Linked: {documents_label}")
    elif attachments:
        meta_parts.append(f"Attachments: {attachments_label}")
    return CollaborationRecordViewModel(
        id=comment.id,
        title=f"@{(comment.author_username or 'unknown').strip() or 'unknown'}",
        status_label="Deleted" if deleted else ("Mentions" if mentions else "Comment"),
        subtitle="This comment was deleted." if deleted else comment.body,
        supporting_text=f"Attachments: {attachments_label}"
        if attachments
        else "No attachment references recorded.",
        meta_text=" | ".join(meta_parts),
        can_primary_action=can_reply,
        can_secondary_action=can_edit,
        can_tertiary_action=can_reply,
        state={
            "taskId": comment.task_id,
            "commentId": comment.id,
            "mentions": list(mentions),
            "attachments": list(attachments),
            "linkedDocuments": list(documents),
            "authorUserId": comment.author_user_id,
            "parentCommentId": comment.parent_comment_id,
            "isReply": bool(comment.parent_comment_id),
            "isEdited": edited,
            "isDeleted": deleted,
            "parentAuthorUsername": comment.parent_author_username,
            "threadDepth": 1 if comment.parent_comment_id else 0,
            "replyCount": max(int(comment.reply_count), 0),
            "canReply": can_reply,
            "canEdit": can_edit,
            "canDelete": can_reply,
            "canReact": can_react,
            "revision": comment.version,
            "deletionReason": comment.deletion_reason or "",
            "reactions": [
                {
                    "emoji": reaction.emoji,
                    "count": reaction.count,
                    "reactorUserIds": list(reaction.reactor_user_ids),
                    "reactedByCurrentUser": reaction.reacted_by_current_user,
                }
                for reaction in reactions
            ],
        },
    )


def to_collaboration_presence_record_view_model(
    presence,
) -> CollaborationRecordViewModel:
    username = (presence.username or "").strip()
    display_name = (presence.display_name or "").strip()
    who_label = (
        f"{display_name} (@{username})"
        if display_name and username
        else display_name or (f"@{username}" if username else "Unknown")
    )
    return CollaborationRecordViewModel(
        id=f"{presence.task_id}:{presence.user_id}",
        title=who_label,
        status_label=str(presence.activity or "").replace("_", " ").title(),
        subtitle=f"Last seen {presence.last_seen_at.strftime('%Y-%m-%d %H:%M')}",
        supporting_text="You are included in this presence view."
        if presence.is_self
        else "",
        meta_text=f"@{username}" if username else "",
        state={
            "taskId": presence.task_id,
            "username": username,
            "userId": presence.user_id,
            "isSelf": presence.is_self,
        },
    )
