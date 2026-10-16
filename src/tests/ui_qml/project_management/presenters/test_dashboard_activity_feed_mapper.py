from datetime import UTC, datetime
from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.dashboard.activity_feed_mapper import to_activity_item


def _item(**overrides):
    fields = dict(
        comment_id="comment-1", task_name="Kickoff task", mentions=(),
        created_at=datetime(2026, 3, 5, 14, 30, tzinfo=UTC),
        author_username="ada", project_name="Project Apollo",
        task_id="task-1", project_id="project-1",
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_maps_actor_subject_and_timestamp_label():
    item = to_activity_item(_item())
    assert item.actor_display == "ada"
    assert item.subject_display == "Project Apollo"
    assert item.occurred_at_label == "2026-03-05 14:30"
    assert item.icon_key == "collaboration"


def test_mention_gets_info_tone_and_badge():
    item = to_activity_item(_item(mentions=("ada",)))
    assert item.tone == "info" and item.badge_label == "Mention"


def test_ordinary_comment_has_no_badge_and_neutral_tone():
    item = to_activity_item(_item())
    assert item.tone == "neutral" and item.badge_label == ""


def test_activation_state_carries_route_and_raw_ids():
    assert to_activity_item(_item()).activation_state == {
        "routeId": "project_management.tasks", "taskId": "task-1",
        "projectId": "project-1", "commentId": "comment-1",
    }


def test_falls_back_to_system_when_actor_is_missing():
    assert to_activity_item(_item(author_username="")).actor_display == "System"
