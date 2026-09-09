from __future__ import annotations

from datetime import datetime, timezone, date

import pytest

from src.core.modules.project_management.domain.collaboration import TaskPresence
from src.core.platform.common.exceptions import ValidationError


def test_task_presence_dto_normalizes_and_validates_fields():
    started_at = datetime(2026, 7, 1, 9, 0, 0)
    last_seen_at = datetime(2026, 7, 1, 9, 5, 0, tzinfo=timezone.utc)

    presence = TaskPresence(
        id=" presence-1 ",
        task_id=" task-1 ",
        user_id=" user-1 ",
        username=" Alice ",
        display_name=" Alice Taylor ",
        activity=" Editing ",
        started_at=started_at,
        last_seen_at=last_seen_at,
    )

    assert presence.id == "presence-1"
    assert presence.task_id == "task-1"
    assert presence.user_id == "user-1"
    assert presence.username == "alice"
    assert presence.display_name == "Alice Taylor"
    assert presence.activity == "editing"
    assert presence.started_at.tzinfo == timezone.utc
    assert presence.last_seen_at.tzinfo == timezone.utc


def test_task_presence_dto_rejects_missing_identity_and_invalid_timestamps():
    with pytest.raises(ValidationError) as exc_task:
        TaskPresence.create(task_id=" ", user_id=None, username="alice")
    assert exc_task.value.code == "TASK_PRESENCE_TASK_REQUIRED"

    with pytest.raises(ValidationError) as exc_username:
        TaskPresence.create(task_id="task-1", user_id=None, username=" ")
    assert exc_username.value.code == "TASK_PRESENCE_USERNAME_REQUIRED"

    with pytest.raises(ValidationError) as exc_range:
        TaskPresence(
            id="presence-2",
            task_id="task-1",
            user_id=None,
            username="alice",
            started_at=datetime(2026, 7, 1, 9, 5, 0, tzinfo=timezone.utc),
            last_seen_at=datetime(2026, 7, 1, 9, 0, 0, tzinfo=timezone.utc),
        )
    assert exc_range.value.code == "TASK_PRESENCE_SEEN_RANGE_INVALID"


def test_collaboration_service_uses_presence_dto_normalization(services):
    project_service = services["project_service"]
    task_service = services["task_service"]
    collaboration_service = services["collaboration_service"]

    project = project_service.create_project("Presence DTO Service Proof")
    task = task_service.create_task(
        project.id,
        "Presence Task",
        start_date=date(2026, 7, 1),
        duration_days=2,
    )

    collaboration_service.touch_task_presence(task.id, activity=" Editing ")
    active = collaboration_service.list_task_presence(task.id)

    assert len(active) == 1
    assert active[0].task_id == task.id
    assert active[0].activity == "editing"
    assert active[0].username == "admin"

    collaboration_service.clear_task_presence(task.id)
    assert collaboration_service.list_task_presence(task.id) == []
