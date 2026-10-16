from dataclasses import asdict
from datetime import UTC, datetime

from src.core.modules.project_management.application.collaboration.mappers.comments import (
    map_comment,
)
from src.core.modules.project_management.domain.collaboration import (
    CollaborationInboxItem,
    TaskComment,
)
from src.ui_qml.modules.project_management.presenters.collaboration.formatting import (
    body_preview,
)
from src.ui_qml.modules.project_management.presenters.tasks.collaboration_mapper import (
    to_collaboration_comment_record_view_model,
)


def test_deleted_task_dto_hides_all_content_and_actions():
    comment = TaskComment.create(
        task_id="task",
        author_user_id="author",
        author_username="author",
        body="private original",
    )
    comment.deleted_at = datetime.now(UTC)
    comment.attachments = ["private-file.txt"]
    comment.mentions = ["private-person"]
    comment.reactions = {"like": ["private-person"]}
    dto = to_collaboration_comment_record_view_model(
        map_comment(comment, principal_user_id="author"),
        linked_documents=[],
        can_manage=True,
        can_read=True,
        principal_user_id="author",
    )
    assert dto.state["isDeleted"]
    assert dto.subtitle == "This comment was deleted."
    assert (
        dto.state["attachments"]
        == dto.state["mentions"]
        == dto.state["reactions"]
        == []
    )
    assert "private" not in str(asdict(dto))


def test_inbox_dto_preserves_typed_tombstone_without_original_body():
    now = datetime.now(UTC)
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
    assert item.is_deleted and item.deleted_at == now
    assert body_preview(item) == "This comment was deleted."
