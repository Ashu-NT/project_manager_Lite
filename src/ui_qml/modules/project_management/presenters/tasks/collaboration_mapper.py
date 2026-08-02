from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationRecordViewModel,
)


def to_collaboration_comment_record_view_model(comment) -> CollaborationRecordViewModel:
    meta_parts = [comment.created_at_label]
    if getattr(comment, "is_edited", False):
        meta_parts.append(f"Edited {comment.updated_at_label}")
    if comment.mentions:
        meta_parts.append(f"Mentions: {comment.mentions_label}")
    if comment.linked_documents:
        meta_parts.append(f"Linked: {comment.linked_documents_label}")
    elif comment.attachments:
        meta_parts.append(f"Attachments: {comment.attachments_label}")
    status_label = "Deleted" if getattr(comment, "is_deleted", False) else ("Mentions" if comment.mentions else "Comment")
    return CollaborationRecordViewModel(
        id=comment.comment_id,
        title=f"@{comment.author_username}",
        status_label=status_label,
        subtitle=comment.body,
        supporting_text=(
            f"Attachments: {comment.attachments_label}"
            if comment.attachments
            else "No attachment references recorded."
        ),
        meta_text=" | ".join(part for part in meta_parts if part),
        can_primary_action=bool(getattr(comment, "can_reply", False)),
        can_secondary_action=bool(getattr(comment, "can_edit", False)),
        can_tertiary_action=bool(getattr(comment, "can_delete", False)),
        state={
            "taskId": comment.task_id,
            "commentId": comment.comment_id,
            "mentions": list(comment.mentions),
            "attachments": list(comment.attachments),
            "linkedDocuments": list(comment.linked_documents),
            "authorUserId": getattr(comment, "author_user_id", None),
            "parentCommentId": getattr(comment, "parent_comment_id", None),
            "isReply": bool(getattr(comment, "is_reply", False)),
            "isEdited": bool(getattr(comment, "is_edited", False)),
            "isDeleted": bool(getattr(comment, "is_deleted", False)),
            "parentAuthorUsername": getattr(comment, "parent_author_username", ""),
            "threadDepth": int(getattr(comment, "thread_depth", 0) or 0),
            "replyCount": int(getattr(comment, "reply_count", 0) or 0),
            "canReply": bool(getattr(comment, "can_reply", False)),
            "canEdit": bool(getattr(comment, "can_edit", False)),
            "canDelete": bool(getattr(comment, "can_delete", False)),
            "canReact": bool(getattr(comment, "can_react", False)),
            "revision": int(getattr(comment, "revision", 1) or 1),
            "deletionReason": str(getattr(comment, "deletion_reason", "") or ""),
            "reactions": [
                {
                    "emoji": reaction.emoji,
                    "count": reaction.count,
                    "reactorUserIds": list(reaction.reactor_user_ids),
                    "reactedByCurrentUser": bool(
                        getattr(reaction, "reacted_by_current_user", False)
                    ),
                }
                for reaction in getattr(comment, "reactions", ())
            ],
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
