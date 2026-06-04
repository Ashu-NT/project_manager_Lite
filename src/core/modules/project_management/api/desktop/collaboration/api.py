"""ProjectManagementCollaborationDesktopApi — desktop API facade."""

from __future__ import annotations

from src.core.modules.project_management.application.collaboration import CollaborationService

from src.core.modules.project_management.api.desktop.collaboration.commands.task_commands import (
    TaskCollaborationPostCommand,
)
from src.core.modules.project_management.api.desktop.collaboration.models.collaboration_models import (
    CollaborationWorkspaceSnapshotDto,
    TaskCollaborationDocumentOptionDescriptor,
    TaskCollaborationMentionOptionDescriptor,
    TaskCollaborationSnapshotDto,
    TaskCollaborationCommentDesktopDto,
)
from src.core.modules.project_management.api.desktop.collaboration.serializers.collaboration_serializers import (
    serialize_inbox_item,
    serialize_notification,
    serialize_presence_item,
    serialize_task_comment,
)
from src.core.modules.project_management.api.desktop.collaboration.utils.formatting import (
    format_document_option_label,
)


class ProjectManagementCollaborationDesktopApi:
    def __init__(
        self,
        *,
        collaboration_service: CollaborationService | None = None,
    ) -> None:
        self._collaboration_service = collaboration_service

    def build_snapshot(self, *, limit: int = 200) -> CollaborationWorkspaceSnapshotDto:
        if self._collaboration_service is None:
            return CollaborationWorkspaceSnapshotDto(
                notifications=(),
                inbox=(),
                recent_activity=(),
                active_presence=(),
            )
        snapshot = self._collaboration_service.list_workspace_snapshot(limit=limit)
        return CollaborationWorkspaceSnapshotDto(
            notifications=tuple(serialize_notification(item) for item in snapshot.notifications),
            inbox=tuple(serialize_inbox_item(item) for item in snapshot.inbox),
            recent_activity=tuple(serialize_inbox_item(item) for item in snapshot.recent_activity),
            active_presence=tuple(serialize_presence_item(item) for item in snapshot.active_presence),
        )

    def mark_task_mentions_read(self, task_id: str) -> None:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            raise ValueError("Task ID is required to mark collaboration mentions as read.")
        self._require_collaboration_service().mark_task_mentions_read(normalized_task_id)

    def touch_task_presence(self, task_id: str, *, activity: str = "reviewing") -> None:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            raise ValueError("Task ID is required to start a presence session.")
        normalized_activity = (activity or "").strip() or "reviewing"
        self._require_collaboration_service().touch_task_presence(
            normalized_task_id, activity=normalized_activity
        )

    def clear_task_presence(self, task_id: str) -> None:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            raise ValueError("Task ID is required to clear a presence session.")
        self._require_collaboration_service().clear_task_presence(normalized_task_id)

    def build_task_snapshot(self, task_id: str) -> TaskCollaborationSnapshotDto:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id or self._collaboration_service is None:
            return TaskCollaborationSnapshotDto(
                comments=(),
                active_presence=(),
                mention_options=(),
                document_options=(),
            )
        service = self._require_collaboration_service()
        comments = sorted(
            service.list_comments(normalized_task_id),
            key=lambda comment: comment.created_at,
            reverse=True,
        )
        documents_by_comment = service.list_comment_documents(normalized_task_id)
        return TaskCollaborationSnapshotDto(
            comments=tuple(
                serialize_task_comment(
                    comment,
                    linked_documents=documents_by_comment.get(comment.id, ()),
                )
                for comment in comments
            ),
            active_presence=tuple(
                serialize_presence_item(item)
                for item in service.list_task_presence(normalized_task_id)
            ),
            mention_options=tuple(
                TaskCollaborationMentionOptionDescriptor(
                    value=candidate.handle,
                    label=candidate.label,
                )
                for candidate in sorted(
                    service.list_mention_candidates(normalized_task_id),
                    key=lambda item: item.label.casefold(),
                )
            ),
            document_options=tuple(
                TaskCollaborationDocumentOptionDescriptor(
                    value=document.id,
                    label=format_document_option_label(document),
                )
                for document in sorted(
                    service.list_available_documents(active_only=True),
                    key=lambda item: (
                        str(getattr(item, "document_code", "") or "").casefold(),
                        str(getattr(item, "title", "") or "").casefold(),
                    ),
                )
            ),
        )

    def post_task_comment(
        self,
        command: TaskCollaborationPostCommand,
    ) -> TaskCollaborationCommentDesktopDto:
        normalized_task_id = (command.task_id or "").strip()
        if not normalized_task_id:
            raise ValueError("Task ID is required to post a collaboration update.")
        service = self._require_collaboration_service()
        comment = service.post_comment(
            task_id=normalized_task_id,
            body=command.body,
            attachments=command.attachments,
            linked_document_ids=command.linked_document_ids,
        )
        linked_documents = service.list_comment_documents(normalized_task_id).get(comment.id, ())
        return serialize_task_comment(comment, linked_documents=linked_documents)

    def _require_collaboration_service(self) -> CollaborationService:
        if self._collaboration_service is None:
            raise RuntimeError(
                "Project management collaboration desktop API is not connected."
            )
        return self._collaboration_service


__all__ = ["ProjectManagementCollaborationDesktopApi"]
