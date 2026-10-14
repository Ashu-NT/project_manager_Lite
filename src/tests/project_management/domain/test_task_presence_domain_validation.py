from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from src.core.modules.project_management.application.collaboration.utils.visibility import (
    new_collaboration_context,
)
from src.core.modules.project_management.domain.collaboration import TaskPresence
from src.core.platform.common.exceptions import ValidationError


def test_task_presence_dto_normalizes_and_validates_fields():
    started_at = datetime(2026, 7, 1, 9, 0, 0)
    last_seen_at = datetime(2026, 7, 1, 9, 5, 0, tzinfo=UTC)

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
    assert presence.started_at.tzinfo == UTC
    assert presence.last_seen_at.tzinfo == UTC


def test_task_presence_dto_rejects_missing_identity_and_invalid_timestamps():
    with pytest.raises(ValidationError) as exc_task:
        TaskPresence.create(task_id=" ", user_id="user-1", username="alice")
    assert exc_task.value.code == "TASK_PRESENCE_TASK_REQUIRED"

    with pytest.raises(ValidationError) as exc_user:
        TaskPresence.create(task_id="task-1", user_id=" ", username="alice")
    assert exc_user.value.code == "TASK_PRESENCE_USER_REQUIRED"

    with pytest.raises(ValidationError) as exc_username:
        TaskPresence.create(task_id="task-1", user_id="user-1", username=" ")
    assert exc_username.value.code == "TASK_PRESENCE_USERNAME_REQUIRED"

    with pytest.raises(ValidationError) as exc_range:
        TaskPresence(
            id="presence-2",
            task_id="task-1",
            user_id="user-1",
            username="alice",
            started_at=datetime(2026, 7, 1, 9, 5, 0, tzinfo=UTC),
            last_seen_at=datetime(2026, 7, 1, 9, 0, 0, tzinfo=UTC),
        )
    assert exc_range.value.code == "TASK_PRESENCE_SEEN_RANGE_INVALID"


def test_presence_handlers_use_presence_dto_normalization(services):
    project_service = services['project_query']
    task_service = services["task_service"]

    project = services['project_create'].create_project("Presence DTO Service Proof")
    task = task_service.create_task(
        project.id,
        "Presence Task",
        start_date=date(2026, 7, 1),
        duration_days=2,
    )

    services["collaboration_presence_commands"].touch_task_presence(task.id, activity=" Editing ")
    active = services["collaboration_presence_query"].list_task_presence(task.id)

    assert len(active) == 1
    assert active[0].task_id == task.id
    assert active[0].activity == "editing"
    assert active[0].username == "admin"

    services["collaboration_presence_commands"].clear_task_presence(task.id)
    assert services["collaboration_presence_query"].list_task_presence(task.id) == []


def test_presence_username_change_keeps_one_user_identity(services):
    principal = services["user_session"].principal
    project = services['project_create'].create_project("Stable presence identity")
    task = services["task_service"].create_task(project.id, "Presence rename")

    with services["collaboration_presence_commands"]._uow_factory.create(context=new_collaboration_context()) as uow:
        first = uow.presence.touch(
            task_id=task.id,
            user_id=principal.user_id,
            username="before-rename",
            display_name="Same Person",
            activity="reviewing",
        )
        uow.commit()
    with services["collaboration_presence_commands"]._uow_factory.create(context=new_collaboration_context()) as uow:
        renamed = uow.presence.touch(
            task_id=task.id,
            user_id=principal.user_id,
            username="after-rename",
            display_name="Same Person",
            activity="editing",
        )
        uow.commit()

    rows = services["collaboration_presence_query"]._presence_repo.list_recent_for_tasks(
        [task.id], since=datetime(2020, 1, 1, tzinfo=UTC)
    )
    assert len(rows) == 1
    assert first.id == renamed.id == rows[0].id
    assert rows[0].user_id == principal.user_id
    assert rows[0].username == "after-rename"
    assert rows[0].activity == "editing"
