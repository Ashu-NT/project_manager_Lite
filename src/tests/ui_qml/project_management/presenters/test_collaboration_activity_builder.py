from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.collaboration.activity_builder import (
    build_activity_collection,
)


def _activity(**overrides) -> SimpleNamespace:
    fields = dict(
        comment_id="comment-1",
        task_id="task-1",
        task_name="Kickoff",
        project_id="project-1",
        project_name="Project Apollo",
        author_username="ada",
        body_preview="Let's align on scope.",
        mentions=(),
        mentions_label="",
        created_at=datetime(2026, 3, 5, 14, 30, tzinfo=timezone.utc),
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_maps_actor_subject_and_timestamp() -> None:
    result = build_activity_collection((_activity(),))

    item = result["items"][0]
    assert item["actorDisplay"] == "ada"
    assert item["subjectDisplay"] == "Project Apollo"
    assert item["occurredAtLabel"] == "2026-03-05 14:30"
    assert item["iconKey"] == "collaboration"


def test_mention_gets_info_tone_and_badge() -> None:
    result = build_activity_collection((_activity(mentions=("ada",), mentions_label="@ada"),))

    item = result["items"][0]
    assert item["tone"] == "info"
    assert item["statusLabel"] == "Mention"


def test_ordinary_comment_has_no_badge_and_neutral_tone() -> None:
    result = build_activity_collection((_activity(),))

    item = result["items"][0]
    assert item["tone"] == "neutral"
    assert item["statusLabel"] == ""


def test_activation_state_carries_route_and_raw_ids_for_navigation_and_lookup() -> None:
    result = build_activity_collection((_activity(),))

    item = result["items"][0]
    assert item["activationState"] == {
        "routeId": "project_management.tasks",
        "projectId": "project-1",
        "projectName": "Project Apollo",
        "taskId": "task-1",
        "commentId": "comment-1",
        "actorUsername": "ada",
        "createdAt": "2026-03-05T14:30:00+00:00",
    }


def test_falls_back_to_system_when_author_is_missing() -> None:
    result = build_activity_collection((_activity(author_username=""),))

    assert result["items"][0]["actorDisplay"] == "System"
