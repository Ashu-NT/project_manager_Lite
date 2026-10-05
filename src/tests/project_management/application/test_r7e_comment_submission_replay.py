import pytest

from src.core.platform.common.exceptions import BusinessRuleError, ValidationError


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


def test_duplicate_primary_key_race_returns_committed_submission(services, monkeypatch) -> None:
    project = services["project_service"].create_project("Replay race")
    task = services["task_service"].create_task(project.id, "Discuss")
    service = services["collaboration_service"]
    first = service.post_comment(
        task_id=task.id, body="One logical post", submission_id="r7e-race-command"
    )
    original_get = service._comment_repo.get
    missed = False

    def miss_first_lookup(comment_id: str):
        nonlocal missed
        if comment_id == first.id and not missed:
            missed = True
            return None
        return original_get(comment_id)

    monkeypatch.setattr(service._comment_repo, "get", miss_first_lookup)
    replay = service.post_comment(
        task_id=task.id, body="One logical post", submission_id="r7e-race-command"
    )

    assert replay.id == first.id
    assert service.query_task_comments_page(task.id).total == 1


def test_deleted_parent_rejects_reply_and_repeated_reactions_are_no_ops(services) -> None:
    project = services["project_service"].create_project("Comment lifecycle")
    task = services["task_service"].create_task(project.id, "Discuss")
    service = services["collaboration_service"]
    parent = service.post_comment(task_id=task.id, body="Parent")
    first_reaction = service.react_to_comment(parent.id, "thumbs-up")
    repeated = service.react_to_comment(parent.id, "thumbs-up")
    assert repeated.version == first_reaction.version
    removed = service.remove_reaction(parent.id, "thumbs-up")
    repeated_remove = service.remove_reaction(parent.id, "thumbs-up")
    assert repeated_remove.version == removed.version

    service.delete_comment(parent.id, expected_revision=removed.version)
    with pytest.raises(BusinessRuleError) as exc:
        service.post_comment(task_id=task.id, body="Late reply", parent_comment_id=parent.id)
    assert exc.value.code == "COLLABORATION_PARENT_COMMENT_DELETED"
    assert service.query_task_comments_page(task.id).total == 1
