import pytest

from src.core.platform.common.exceptions import ValidationError


def test_same_comment_submission_replays_without_duplicate_and_new_draft_is_distinct(
    services,
) -> None:
    project = services["project_service"].create_project("Replay comments")
    task = services["task_service"].create_task(project.id, "Discuss")
    service = services["collaboration_service"]

    first = service.post_comment(
        task_id=task.id, body="Same visible text", submission_id="r7e-command-one"
    )
    replay = service.post_comment(
        task_id=task.id, body="Same visible text", submission_id="r7e-command-one"
    )
    second = service.post_comment(
        task_id=task.id, body="Same visible text", submission_id="r7e-command-two"
    )

    assert first.id == replay.id == "r7e-command-one"
    assert second.id == "r7e-command-two"
    assert first.submission_hash == replay.submission_hash
    assert service.query_task_comments_page(task.id).total == 2

    with pytest.raises(ValidationError) as conflict:
        service.post_comment(
            task_id=task.id, body="Changed text", submission_id="r7e-command-one"
        )
    assert conflict.value.code == "COLLABORATION_SUBMISSION_CONFLICT"
    assert service.query_task_comments_page(task.id).total == 2
