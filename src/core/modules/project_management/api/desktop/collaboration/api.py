"""ProjectManagementCollaborationDesktopApi — desktop API facade."""

from __future__ import annotations

from typing import TypeVar

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
from src.core.modules.project_management.application.collaboration.commands import (
    CollaborationCommentCommandHandler,
    CollaborationCommentEngagementHandler,
    CollaborationPresenceCommandHandler,
)
from src.core.modules.project_management.application.collaboration.queries import (
    CollaborationCommentQueryHandler,
    CollaborationDocumentQueryHandler,
    CollaborationInboxQueryHandler,
    CollaborationPresenceQueryHandler,
)
from src.core.platform.common.exceptions import ConfigurationError, ValidationError

_HandlerT = TypeVar("_HandlerT")


def _require(handler: _HandlerT | None) -> _HandlerT:
    if handler is None:
        raise ConfigurationError(
            "Project management collaboration desktop API is not connected."
        )
    return handler
from src.core.modules.project_management.application.collaboration.dto.commands.comment_reactions import (
    TaskCollaborationReactionCommand,
)
from src.core.modules.project_management.application.collaboration.dto.commands.task_comments import (
    TaskCollaborationDeleteCommand,
    TaskCollaborationEditCommand,
    TaskCollaborationPostCommand,
)


class ProjectManagementCollaborationDesktopApi:
    def __init__(
        self,
        *,
        inbox_query: CollaborationInboxQueryHandler | None = None,
        comment_query: CollaborationCommentQueryHandler | None = None,
        document_query: CollaborationDocumentQueryHandler | None = None,
        presence_query: CollaborationPresenceQueryHandler | None = None,
        comment_commands: CollaborationCommentCommandHandler | None = None,
        comment_engagement: CollaborationCommentEngagementHandler | None = None,
        presence_commands: CollaborationPresenceCommandHandler | None = None,
    ) -> None:
        self._inbox_query = inbox_query
        self._comment_query = comment_query
        self._document_query = document_query
        self._presence_query = presence_query
        self._comment_commands = comment_commands
        self._comment_engagement = comment_engagement
        self._presence_commands = presence_commands

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
        if self._inbox_query is None:
            return CollaborationCommentPageDto((), 0, page, page_size)
        result = self._inbox_query.query_inbox_page(
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
        if self._inbox_query is None:
            return CollaborationCommentPageDto((), 0, page, page_size)
        result = self._inbox_query.query_mentions_page(
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
        if self._inbox_query is None:
            return ()
        return tuple(
            serialize_inbox_item(item)
            for item in self._inbox_query.list_recent_activity(
                project_id=project_id,
                author_username=author_username,
                created_since=created_since,
                limit=limit,
            )
        )

    def list_active_presence(self) -> tuple[CollaborationPresenceDesktopDto, ...]:
        if self._presence_query is None:
            return ()
        return tuple(
            serialize_presence_item(item)
            for item in self._presence_query.list_active_presence()
        )

    def list_context_options(self) -> CollaborationContextOptionsDto:
        if self._inbox_query is None:
            return CollaborationContextOptionsDto((), ())
        context = self._inbox_query.list_workspace_context()
        return CollaborationContextOptionsDto(
            projects=context.projects,
            people=context.people,
        )

    def mark_task_mentions_read(self, task_id: str) -> None:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            raise ValidationError("Task ID is required to mark collaboration mentions as read.", code="TASK_ID_REQUIRED")
        _require(self._comment_engagement).mark_task_mentions_read(normalized_task_id)

    def touch_task_presence(self, task_id: str, *, activity: str = "reviewing") -> None:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            raise ValidationError("Task ID is required to start a presence session.", code="TASK_ID_REQUIRED")
        normalized_activity = (activity or "").strip() or "reviewing"
        _require(self._presence_commands).touch_task_presence(
            normalized_task_id, activity=normalized_activity
        )

    def clear_task_presence(self, task_id: str) -> None:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            raise ValidationError("Task ID is required to clear a presence session.", code="TASK_ID_REQUIRED")
        _require(self._presence_commands).clear_task_presence(normalized_task_id)

    def build_task_snapshot(
        self, task_id: str, *, page: int = 1, page_size: int = 25
    ) -> TaskCollaborationSnapshotDto:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id or self._comment_query is None:
            return TaskCollaborationSnapshotDto(
                comments=(),
                active_presence=(),
                mention_options=(),
                document_options=(),
            )
        comment_query = self._comment_query
        document_query = _require(self._document_query)
        comments = comment_query.query_task_comments_page(
            normalized_task_id, page=page, page_size=page_size
        )
        action_context = comment_query.get_task_comment_action_context(normalized_task_id)
        documents_by_comment = document_query.list_comment_documents_for_ids(
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
                for item in _require(self._presence_query).list_task_presence(normalized_task_id)
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
                    comment_query.list_mention_candidates(normalized_task_id, limit=50),
                    key=lambda item: item.label.casefold(),
                )
            ),
            document_options=tuple(
                TaskCollaborationDocumentOptionDescriptor(
                    value=document.id,
                    label=format_document_option_label(document),
                )
                for document in sorted(
                    document_query.search_available_documents(normalized_task_id, limit=50),
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
        candidates = _require(self._comment_query).list_mention_candidates(
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
        documents = _require(self._document_query).search_available_documents(
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
            raise ValidationError("Task ID is required to post a collaboration update.", code="TASK_ID_REQUIRED")
        comment = _require(self._comment_commands).post_comment(command)
        linked_documents = _require(self._document_query).list_comment_documents_for_ids(
            normalized_task_id, (comment.id,)
        ).get(comment.id, ())
        return serialize_task_comment(comment, linked_documents=linked_documents)

    def edit_task_comment(
        self,
        command: TaskCollaborationEditCommand,
    ) -> TaskCollaborationCommentDesktopDto:
        normalized_comment_id = (command.comment_id or "").strip()
        if not normalized_comment_id:
            raise ValidationError("Comment ID is required to edit a collaboration update.", code="COMMENT_ID_REQUIRED")
        comment = _require(self._comment_commands).edit_comment(command)
        linked_documents = _require(self._document_query).list_comment_documents_for_ids(
            comment.task_id, (comment.id,)
        ).get(comment.id, ())
        return serialize_task_comment(comment, linked_documents=linked_documents)

    def delete_task_comment(
        self,
        command: TaskCollaborationDeleteCommand,
    ) -> TaskCollaborationCommentDesktopDto:
        normalized_comment_id = (command.comment_id or "").strip()
        if not normalized_comment_id:
            raise ValidationError("Comment ID is required to delete a collaboration update.", code="COMMENT_ID_REQUIRED")
        comment = _require(self._comment_commands).delete_comment(command)
        linked_documents = _require(self._document_query).list_comment_documents_for_ids(
            comment.task_id, (comment.id,)
        ).get(comment.id, ())
        return serialize_task_comment(comment, linked_documents=linked_documents)

    def react_to_task_comment(
        self,
        command: TaskCollaborationReactionCommand,
    ) -> TaskCollaborationCommentDesktopDto:
        normalized_comment_id = (command.comment_id or "").strip()
        if not normalized_comment_id:
            raise ValidationError("Comment ID is required to react to a collaboration update.", code="COMMENT_ID_REQUIRED")
        comment = _require(self._comment_engagement).react_to_comment(command)
        linked_documents = _require(self._document_query).list_comment_documents_for_ids(
            comment.task_id, (comment.id,)
        ).get(comment.id, ())
        return serialize_task_comment(comment, linked_documents=linked_documents)

    def remove_task_comment_reaction(
        self,
        command: TaskCollaborationReactionCommand,
    ) -> TaskCollaborationCommentDesktopDto:
        normalized_comment_id = (command.comment_id or "").strip()
        if not normalized_comment_id:
            raise ValidationError("Comment ID is required to remove a reaction.", code="COMMENT_ID_REQUIRED")
        comment = _require(self._comment_engagement).remove_reaction(command)
        linked_documents = _require(self._document_query).list_comment_documents_for_ids(
            comment.task_id, (comment.id,)
        ).get(comment.id, ())
        return serialize_task_comment(comment, linked_documents=linked_documents)


__all__ = ["ProjectManagementCollaborationDesktopApi"]
