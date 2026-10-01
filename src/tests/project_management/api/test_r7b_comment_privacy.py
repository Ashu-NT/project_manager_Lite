from dataclasses import asdict
from datetime import datetime, timezone

from src.core.modules.project_management.api.desktop.collaboration.serializers.collaboration_serializers import (
    serialize_inbox_item,
    serialize_task_comment,
)
from src.core.modules.project_management.domain.collaboration import (
    CollaborationInboxItem,
    TaskComment,
)


def test_deleted_task_dto_hides_all_content_and_actions():
    comment = TaskComment.create(
        task_id="task",
        author_user_id="author",
        author_username="author",
        body="private original",
    )
    comment.deleted_at = datetime.now(timezone.utc)
    comment.attachments = ["private-file.txt"]
    comment.mentions = ["private-person"]
    comment.reactions = {"like": ["private-person"]}
    dto = serialize_task_comment(
        comment,
        linked_documents=[],
        can_manage=True,
        can_read=True,
        principal_user_id="author",
    )
    assert dto.is_deleted
    assert dto.body == "This comment was deleted."
    assert dto.attachments == dto.mentions == dto.reactions == ()
    assert "private" not in str(asdict(dto))


def test_inbox_dto_preserves_typed_tombstone_without_original_body():
    now = datetime.now(timezone.utc)
    item = CollaborationInboxItem(
        comment_id="comment",
        task_id="task",
        task_name="Task",
        project_id="project",
        project_name="Project",
        author_username="author",
        body_preview="",
        mentions=[],
        created_at=now,
        unread=False,
        is_deleted=True,
        deleted_at=now,
    )
    dto = serialize_inbox_item(item)
    assert dto.is_deleted and dto.deleted_at == now
    assert dto.body_preview == "This comment was deleted."
