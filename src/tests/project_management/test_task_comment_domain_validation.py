from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.application.collaboration.services.collaboration_service import (
    CollaborationService,
)
from src.core.modules.project_management.domain.collaboration import TaskComment
from src.core.platform.common.exceptions import NotFoundError, ValidationError


class _FakeSession:
    def __init__(self) -> None:
        self.commit_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        return None


class _FakeCommentRepo:
    def __init__(self) -> None:
        self._comments: dict[str, TaskComment] = {}

    def add(self, comment: TaskComment) -> None:
        self._comments[comment.id] = comment

    def update(self, comment: TaskComment) -> None:
        if comment.id not in self._comments:
            raise NotFoundError("Task comment not found.")
        self._comments[comment.id] = comment

    def get(self, comment_id: str) -> TaskComment | None:
        return self._comments.get(comment_id)

    def list_by_task(self, task_id: str) -> list[TaskComment]:
        return [
            comment
            for comment in sorted(
                self._comments.values(),
                key=lambda item: item.created_at,
            )
            if comment.task_id == task_id
        ]

    def list_recent_for_tasks(self, task_ids: list[str], limit: int = 200) -> list[TaskComment]:
        selected = [
            comment
            for comment in self._comments.values()
            if comment.task_id in set(task_ids)
        ]
        selected.sort(key=lambda item: item.created_at, reverse=True)
        return selected[:limit]


class _FakeTaskRepo:
    def __init__(self, tasks: dict[str, object] | None = None) -> None:
        self._tasks = tasks or {
            "task-1": SimpleNamespace(id="task-1", project_id="proj-1"),
        }

    def get(self, task_id: str):
        return self._tasks.get(task_id)


class _FakeUserRepo:
    def __init__(self, users: dict[str, object] | None = None) -> None:
        self._users = users or {
            "user-1": SimpleNamespace(
                id="user-1",
                username="alex",
                display_name="Alex Planner",
                is_active=True,
            ),
            "user-2": SimpleNamespace(
                id="user-2",
                username="planner",
                display_name="Project Planner",
                is_active=True,
            ),
        }

    def get(self, user_id: str):
        return self._users.get(user_id)


class _FakeProjectMembershipRepo:
    def __init__(self, memberships: dict[str, list[object]] | None = None) -> None:
        self._memberships = memberships or {
            "proj-1": [
                SimpleNamespace(
                    user_id="user-2",
                    permission_codes=["collaboration.read"],
                    scope_role="viewer",
                )
            ]
        }

    def list_by_project(self, project_id: str) -> list[object]:
        return list(self._memberships.get(project_id, []))


class _FakeUserSession:
    def __init__(
        self,
        *,
        user_id: str = "user-1",
        username: str = "alex",
        display_name: str = "Alex Planner",
    ) -> None:
        self.principal = SimpleNamespace(
            user_id=user_id,
            username=username,
            display_name=display_name,
        )

    def has_project_permission(self, _project_id: str, _permission_code: str) -> bool:
        return True


def _make_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    user_id: str = "user-1",
    username: str = "alex",
    display_name: str = "Alex Planner",
) -> CollaborationService:
    monkeypatch.setattr(
        "src.core.modules.project_management.application.collaboration.commands.collaboration_comments.require_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.collaboration.commands.collaboration_comments.require_project_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.collaboration.commands.collaboration_comments.store_task_comment_attachments",
        lambda **kwargs: [
            str(item).strip()
            for item in (kwargs.get("attachments") or [])
            if str(item).strip()
        ],
    )
    return CollaborationService(
        session=_FakeSession(),
        comment_repo=_FakeCommentRepo(),
        presence_repo=object(),
        task_repo=_FakeTaskRepo(),
        project_repo=object(),
        user_repo=_FakeUserRepo(),
        audit_repo=object(),
        project_membership_repo=_FakeProjectMembershipRepo(),
        document_integration_service=None,
        user_session=_FakeUserSession(
            user_id=user_id,
            username=username,
            display_name=display_name,
        ),
        tenant_context_service=object(),
    )


def test_task_comment_dto_normalizes_local_fields():
    comment = TaskComment.create(
        task_id="  task-1  ",
        author_user_id="  user-1  ",
        author_username="  Alex Planner  ",
        body="  Need review before Friday.  ",
        mentions=["Planner", "planner", " "],
        mentioned_user_ids=[" user-2 ", "user-2"],
        attachments=[" handover.txt ", "", "ticket-42", " handover.txt "],
        read_by=["Alex", "alex", " "],
        read_by_user_ids=[" user-1 ", "user-1"],
    )

    assert comment.task_id == "task-1"
    assert comment.author_user_id == "user-1"
    assert comment.author_username == "Alex Planner"
    assert comment.body == "Need review before Friday."
    assert comment.mentions == ["planner"]
    assert comment.mentioned_user_ids == ["user-2"]
    assert comment.attachments == ["handover.txt", "ticket-42", "handover.txt"]
    assert comment.read_by == ["alex"]
    assert comment.read_by_user_ids == ["user-1"]


def test_task_comment_dto_rejects_invalid_local_fields():
    with pytest.raises(ValidationError) as exc_task:
        TaskComment.create(
            task_id=" ",
            author_user_id="user-1",
            author_username="alex",
            body="Valid",
        )
    assert exc_task.value.code == "COLLABORATION_TASK_REQUIRED"

    with pytest.raises(ValidationError) as exc_body:
        TaskComment.create(
            task_id="task-1",
            author_user_id="user-1",
            author_username="alex",
            body="   ",
        )
    assert exc_body.value.code == "COLLABORATION_BODY_REQUIRED"

    with pytest.raises(ValidationError) as exc_timestamp:
        TaskComment(
            id="comment-1",
            task_id="task-1",
            author_user_id="user-1",
            author_username="alex",
            body="Valid",
            created_at="2026-07-24T09:00:00Z",
        )
    assert exc_timestamp.value.code == "COLLABORATION_TIMESTAMP_INVALID"


def test_collaboration_service_post_comment_uses_domain_validation(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(monkeypatch)

    comment = service.post_comment(
        task_id="task-1",
        body="  Please review @planner  ",
        attachments=[" handover.txt ", "", "ticket-42"],
    )

    assert comment.task_id == "task-1"
    assert comment.author_user_id == "user-1"
    assert comment.author_username == "alex"
    assert comment.body == "Please review @planner"
    assert comment.mentions == ["planner"]
    assert comment.mentioned_user_ids == ["user-2"]
    assert comment.attachments == ["handover.txt", "ticket-42"]
    assert service._session.commit_calls == 1

    with pytest.raises(ValidationError) as exc:
        service.post_comment(task_id="task-1", body="   ")
    assert exc.value.code == "COLLABORATION_BODY_REQUIRED"


def test_collaboration_service_marks_mentions_read_idempotently(
    monkeypatch: pytest.MonkeyPatch,
):
    service = _make_service(
        monkeypatch,
        user_id="user-2",
        username="planner",
        display_name="Project Planner",
    )

    mentioned = TaskComment.create(
        task_id="task-1",
        author_user_id="user-1",
        author_username="alex",
        body="Please review this update.",
        mentions=["planner"],
        mentioned_user_ids=["user-2"],
    )
    not_mentioned = TaskComment.create(
        task_id="task-1",
        author_user_id="user-1",
        author_username="alex",
        body="General note.",
        mentions=["alex"],
        mentioned_user_ids=["user-1"],
    )
    service._comment_repo.add(mentioned)
    service._comment_repo.add(not_mentioned)

    service.mark_task_mentions_read("task-1")

    stored = service._comment_repo.get(mentioned.id)
    assert stored is not None
    assert stored.read_by == ["planner"]
    assert stored.read_by_user_ids == ["user-2"]
    assert service._session.commit_calls == 1

    unchanged = service._comment_repo.get(not_mentioned.id)
    assert unchanged is not None
    assert unchanged.read_by == []
    assert unchanged.read_by_user_ids == []

    service.mark_task_mentions_read("task-1")
    assert service._session.commit_calls == 1
