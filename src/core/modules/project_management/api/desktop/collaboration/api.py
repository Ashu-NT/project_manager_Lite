"""ProjectManagementCollaborationDesktopApi — desktop API facade."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.collaboration.commands.task_commands import (
    TaskCollaborationDeleteCommand,
    TaskCollaborationEditCommand,
    TaskCollaborationPostCommand,
    TaskCollaborationReactionCommand,
)
from src.core.modules.project_management.api.desktop.collaboration.models.collaboration_models import (
    CollaborationCommentPageDto,
    CollaborationContextOptionsDto,
    CollaborationInboxDesktopDto,
    CollaborationPresenceDesktopDto,
    TaskCollaborationCommentDesktopDto,
    TaskCollaborationDocumentOptionDescriptor,
    TaskCollaborationMentionOptionDescriptor,
    TaskCollaborationSnapshotDto,
)
from src.core.modules.project_management.api.desktop.collaboration.serializers.collaboration_serializers import (
    serialize_inbox_item,
    serialize_presence_item,
    serialize_task_comment,
)
from src.core.modules.project_management.api.desktop.collaboration.utils.formatting import (
    format_document_option_label,
)
from src.core.modules.project_management.application.collaboration import (
    CollaborationService,
)


class ProjectManagementCollaborationDesktopApi:
    def __init__(
        self,
        *,
        collaboration_service: CollaborationService | None = None,
    ) -> None:
        self._collaboration_service = collaboration_service

    def query_inbox_page(
        self,
        *,
        project_id: str | None = None,
        author_username: str | None = None,
        search_text: str = "",
        created_since=None,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> CollaborationCommentPageDto:
        if self._collaboration_service is None:
            return CollaborationCommentPageDto((), 0, page, page_size)
        result = self._collaboration_service.query_inbox_page(
            project_id=project_id,
            author_username=author_username,
            search_text=search_text,
            created_since=created_since,
            unread_only=unread_only,
            page=page,
            page_size=page_size,
        )
        return CollaborationCommentPageDto(
            items=tuple(serialize_inbox_item(item) for item in result.items),
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

    def query_mentions_page(
        self,
        *,
        project_id: str | None = None,
        author_username: str | None = None,
        search_text: str = "",
        created_since=None,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> CollaborationCommentPageDto:
        if self._collaboration_service is None:
            return CollaborationCommentPageDto((), 0, page, page_size)
        result = self._collaboration_service.query_mentions_page(
            project_id=project_id,
            author_username=author_username,
            search_text=search_text,
            created_since=created_since,
            unread_only=unread_only,
            page=page,
            page_size=page_size,
        )
        return CollaborationCommentPageDto(
            items=tuple(serialize_inbox_item(item) for item in result.items),
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

    def list_recent_activity(
        self,
        *,
        project_id: str | None = None,
        author_username: str | None = None,
        created_since=None,
        limit: int = 100,
    ) -> tuple[CollaborationInboxDesktopDto, ...]:
        if self._collaboration_service is None:
            return ()
        return tuple(
            serialize_inbox_item(item)
            for item in self._collaboration_service.list_recent_activity(
                project_id=project_id,
                author_username=author_username,
                created_since=created_since,
                limit=limit,
            )
        )

    def list_active_presence(self) -> tuple[CollaborationPresenceDesktopDto, ...]:
        if self._collaboration_service is None:
            return ()
        return tuple(
            serialize_presence_item(item)
            for item in self._collaboration_service.list_active_presence()
        )

    def list_context_options(self) -> CollaborationContextOptionsDto:
        if self._collaboration_service is None:
            return CollaborationContextOptionsDto((), ())
        context = self._collaboration_service.list_workspace_context()
        return CollaborationContextOptionsDto(
            projects=context.projects,
            people=context.people,
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

    def build_task_snapshot(
        self, task_id: str, *, page: int = 1, page_size: int = 25
    ) -> TaskCollaborationSnapshotDto:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id or self._collaboration_service is None:
            return TaskCollaborationSnapshotDto(
                comments=(),
                active_presence=(),
                mention_options=(),
                document_options=(),
            )
        service = self._require_collaboration_service()
        comments = service.query_task_comments_page(
            normalized_task_id, page=page, page_size=page_size
        )
        action_context = service.get_task_comment_action_context(normalized_task_id)
        documents_by_comment = service.list_comment_documents_for_ids(
            normalized_task_id, tuple(comment.id for comment in comments.items)
        )
        return TaskCollaborationSnapshotDto(
            comments=tuple(
                serialize_task_comment(
                    comment,
                    linked_documents=documents_by_comment.get(comment.id, ()),
                    principal_user_id=action_context.principal_user_id,
                    can_manage=action_context.can_manage,
                    can_read=action_context.can_read,
                    parent_author_username=comment.parent_author_username,
                    thread_depth=1 if comment.parent_comment_id else 0,
                    reply_count=comment.reply_count,
                )
                for comment in comments.items
            ),
            active_presence=tuple(
                serialize_presence_item(item)
                for item in service.list_task_presence(normalized_task_id)
            ),
            mention_options=(
                TaskCollaborationMentionOptionDescriptor(
                    value="everyone",
                    label="@everyone  Mention everyone with access to this task",
                ),
            )
            + tuple(
                TaskCollaborationMentionOptionDescriptor(
                    value=candidate.handle,
                    label=candidate.label,
                )
                for candidate in sorted(
                    service.list_mention_candidates(normalized_task_id, limit=50),
                    key=lambda item: item.label.casefold(),
                )
            ),
            document_options=tuple(
                TaskCollaborationDocumentOptionDescriptor(
                    value=document.id,
                    label=format_document_option_label(document),
                )
                for document in sorted(
                    service.search_available_documents(normalized_task_id, limit=50),
                    key=lambda item: (
                        str(getattr(item, "document_code", "") or "").casefold(),
                        str(getattr(item, "title", "") or "").casefold(),
                    ),
                )
            ),
            comment_total=comments.total,
            comment_page=comments.page,
            comment_page_size=comments.page_size,
        )

    def search_task_mention_options(
        self, task_id: str, query: str
    ) -> tuple[TaskCollaborationMentionOptionDescriptor, ...]:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            return ()
        candidates = self._require_collaboration_service().list_mention_candidates(
            normalized_task_id, query=(query or "").strip()[:128], limit=50
        )
        return (
            TaskCollaborationMentionOptionDescriptor(
                value="everyone",
                label="@everyone  Mention everyone with access to this task",
            ),
        ) + tuple(
            TaskCollaborationMentionOptionDescriptor(
                value=candidate.handle, label=candidate.label
            )
            for candidate in candidates
        )

    def search_task_document_options(
        self, task_id: str, query: str
    ) -> tuple[TaskCollaborationDocumentOptionDescriptor, ...]:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            return ()
        documents = self._require_collaboration_service().search_available_documents(
            normalized_task_id, query=(query or "").strip()[:128], limit=50
        )
        return tuple(
            TaskCollaborationDocumentOptionDescriptor(
                value=document.id, label=format_document_option_label(document)
            )
            for document in documents
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
            parent_comment_id=getattr(command, "parent_comment_id", None),
            submission_id=command.submission_id,
        )
        linked_documents = service.list_comment_documents_for_ids(
            normalized_task_id, (comment.id,)
        ).get(comment.id, ())
        return serialize_task_comment(comment, linked_documents=linked_documents)

    def edit_task_comment(
        self,
        command: TaskCollaborationEditCommand,
    ) -> TaskCollaborationCommentDesktopDto:
        normalized_comment_id = (command.comment_id or "").strip()
        if not normalized_comment_id:
            raise ValueError("Comment ID is required to edit a collaboration update.")
        service = self._require_collaboration_service()
        comment = service.edit_comment(
            normalized_comment_id,
            command.body,
            expected_revision=command.expected_revision,
        )
        linked_documents = service.list_comment_documents_for_ids(
            comment.task_id, (comment.id,)
        ).get(comment.id, ())
        return serialize_task_comment(comment, linked_documents=linked_documents)

    def delete_task_comment(
        self,
        command: TaskCollaborationDeleteCommand,
    ) -> TaskCollaborationCommentDesktopDto:
        normalized_comment_id = (command.comment_id or "").strip()
        if not normalized_comment_id:
            raise ValueError("Comment ID is required to delete a collaboration update.")
        service = self._require_collaboration_service()
        comment = service.delete_comment(
            normalized_comment_id,
            expected_revision=command.expected_revision,
            reason=command.reason,
        )
        linked_documents = service.list_comment_documents_for_ids(
            comment.task_id, (comment.id,)
        ).get(comment.id, ())
        return serialize_task_comment(comment, linked_documents=linked_documents)

    def react_to_task_comment(
        self,
        command: TaskCollaborationReactionCommand,
    ) -> TaskCollaborationCommentDesktopDto:
        normalized_comment_id = (command.comment_id or "").strip()
        if not normalized_comment_id:
            raise ValueError("Comment ID is required to react to a collaboration update.")
        service = self._require_collaboration_service()
        comment = service.react_to_comment(normalized_comment_id, command.emoji)
        linked_documents = service.list_comment_documents_for_ids(
            comment.task_id, (comment.id,)
        ).get(comment.id, ())
        return serialize_task_comment(comment, linked_documents=linked_documents)

    def remove_task_comment_reaction(
        self,
        command: TaskCollaborationReactionCommand,
    ) -> TaskCollaborationCommentDesktopDto:
        normalized_comment_id = (command.comment_id or "").strip()
        if not normalized_comment_id:
            raise ValueError("Comment ID is required to remove a reaction.")
        service = self._require_collaboration_service()
        comment = service.remove_reaction(normalized_comment_id, command.emoji)
        linked_documents = service.list_comment_documents_for_ids(
            comment.task_id, (comment.id,)
        ).get(comment.id, ())
        return serialize_task_comment(comment, linked_documents=linked_documents)

    def _require_collaboration_service(self) -> CollaborationService:
        if self._collaboration_service is None:
            raise RuntimeError(
                "Project management collaboration desktop API is not connected."
            )
        return self._collaboration_service


__all__ = ["ProjectManagementCollaborationDesktopApi"]
