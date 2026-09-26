from __future__ import annotations

from datetime import datetime, timezone

from src.core.modules.project_management.api.desktop.dashboard.models.activity_feed import (
    ProjectDashboardActivityFeedDescriptor,
    ProjectDashboardActivityItemDescriptor,
)
from src.ui_qml.modules.project_management.presenters.dashboard.activity_feed_mapper import (
    to_activity_feed,
)


def _item(**overrides) -> ProjectDashboardActivityItemDescriptor:
    fields = dict(
        id="comment-1",
        title="Kickoff task update",
        status_label="",
        occurred_at=datetime(2026, 3, 5, 14, 30, tzinfo=timezone.utc),
        actor_display="ada",
        subject_display="Project Apollo",
        route_id="project_management.tasks",
        state={"taskId": "task-1", "projectId": "project-1", "commentId": "comment-1"},
    )
    fields.update(overrides)
    return ProjectDashboardActivityItemDescriptor(**fields)


def test_returns_none_when_feed_is_none() -> None:
    assert to_activity_feed(None) is None


def test_maps_actor_subject_and_timestamp_label() -> None:
    feed = ProjectDashboardActivityFeedDescriptor(title="Recent Activity", items=(_item(),))

    result = to_activity_feed(feed)

    item = result["items"][0]
    assert item["actorDisplay"] == "ada"
    assert item["subjectDisplay"] == "Project Apollo"
    assert item["occurredAtLabel"] == "2026-03-05 14:30"
    assert item["iconKey"] == "collaboration"


def test_mention_gets_info_tone_and_badge() -> None:
    feed = ProjectDashboardActivityFeedDescriptor(title="Recent Activity", items=(_item(status_label="Mention"),))

    item = to_activity_feed(feed)["items"][0]

    assert item["tone"] == "info"
    assert item["badgeLabel"] == "Mention"


def test_ordinary_comment_has_no_badge_and_neutral_tone() -> None:
    feed = ProjectDashboardActivityFeedDescriptor(title="Recent Activity", items=(_item(status_label=""),))

    item = to_activity_feed(feed)["items"][0]

    assert item["tone"] == "neutral"
    assert item["badgeLabel"] == ""


def test_activation_state_carries_route_and_raw_ids() -> None:
    feed = ProjectDashboardActivityFeedDescriptor(title="Recent Activity", items=(_item(),))

    item = to_activity_feed(feed)["items"][0]

    assert item["activationState"] == {
        "routeId": "project_management.tasks",
        "taskId": "task-1",
        "projectId": "project-1",
        "commentId": "comment-1",
    }


def test_no_activation_state_without_route_id() -> None:
    feed = ProjectDashboardActivityFeedDescriptor(title="Recent Activity", items=(_item(route_id=""),))

    item = to_activity_feed(feed)["items"][0]

    assert item["activationState"] is None


def test_falls_back_to_system_when_actor_is_missing() -> None:
    feed = ProjectDashboardActivityFeedDescriptor(title="Recent Activity", items=(_item(actor_display=""),))

    item = to_activity_feed(feed)["items"][0]

    assert item["actorDisplay"] == "System"
