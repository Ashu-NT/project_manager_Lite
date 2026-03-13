from infra.modules.project_management.collaboration_store import TaskCollaborationStore


def test_unread_mentions_count_for_aliases_counts_single_comment_once(tmp_path):
    store = TaskCollaborationStore(storage_path=tmp_path / "comments.json")
    store.add_comment(
        task_id="task-1",
        author="alice",
        body="Please review this @bob and @robert",
        attachments=[],
    )

    assert store.unread_mentions_count_for_users(["bob", "robert"]) == 1


def test_marking_one_alias_as_read_marks_alias_group_as_read(tmp_path):
    store = TaskCollaborationStore(storage_path=tmp_path / "comments.json")
    store.add_comment(
        task_id="task-1",
        author="alice",
        body="Need input from @bob and @robert",
        attachments=[],
    )
    assert store.unread_mentions_count_for_users(["bob", "robert"]) == 1

    store.mark_task_mentions_read(task_id="task-1", username="robert")
    assert store.unread_mentions_count_for_users(["bob", "robert"]) == 0
