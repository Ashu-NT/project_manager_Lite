from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.application.collaboration.services.collaboration_service import (
    CollaborationService,
)
from src.core.modules.project_management.domain.collaboration import TaskComment
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError


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
        comment.version += 1
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


class _FakeRole:
    def __init__(self, role_id: str, name: str) -> None:
        self.id = role_id
        self.name = name


class _FakeRoleRepo:
    def __init__(self, roles: dict[str, _FakeRole]) -> None:
        self._roles = roles

    def get_by_name(self, name: str):
        return self._roles.get(name)


class _FakeRoleBinding:
    def __init__(self, principal_id: str, actual_scope_type: str, actual_scope_id: str) -> None:
        self.principal_id = principal_id
        self.actual_scope_type = actual_scope_type
        self.actual_scope_id = actual_scope_id


class _FakeRoleBindingRepo:
    def __init__(self, bindings_by_role: dict[str, list[_FakeRoleBinding]]) -> None:
        self._bindings_by_role = bindings_by_role

    def list_active_for_role(self, role_id: str, *, tenant_id: str) -> list[_FakeRoleBinding]:
        return list(self._bindings_by_role.get(role_id, []))


class _FakeTenantContextService:
    def get_active_tenant_id(self) -> str:
        return "tenant-1"


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

    def has_permission(self, _permission_code: str) -> bool:
        return True

    def has_scope_permission(
        self,
        scope_type: str,
        scope_id: str,
        permission_code: str,
    ) -> bool:
        return scope_type == "project" and self.has_project_permission(
            scope_id,
            permission_code,
        )


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
        workspace_reader=object(),
        document_integration_service=None,
        user_session=_FakeUserSession(
            user_id=user_id,
            username=username,
            display_name=display_name,
        ),
        tenant_context_service=_FakeTenantContextService(),
        role_repo=_FakeRoleRepo({"project_viewer": _FakeRole("role-viewer", "project_viewer")}),
        role_binding_repo=_FakeRoleBindingRepo(
            {"role-viewer": [_FakeRoleBinding("user-2", "project", "proj-1")]}
        ),
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


def test_comment_action_context_is_computed_from_authenticated_scope(
    monkeypatch: pytest.MonkeyPatch,
):
    service = _make_service(monkeypatch)

    action_context = service.get_task_comment_action_context("task-1")

    assert action_context.principal_user_id == "user-1"
    assert action_context.can_read is True
    assert action_context.can_manage is True


# ---------------------------------------------------------------------------
# Edit / soft-delete / threading / reactions (Phase 4)
# ---------------------------------------------------------------------------


def test_edit_comment_updates_body_and_sets_updated_at(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(monkeypatch)
    comment = service.post_comment(task_id="task-1", body="Original text")
    assert comment.updated_at is None

    edited = service.edit_comment(
        comment.id,
        "Revised text @planner",
        expected_revision=1,
    )

    assert edited.body == "Revised text @planner"
    assert edited.mentioned_user_ids == ["user-2"]
    assert edited.updated_at is not None
    assert edited.version == 2


def test_edit_comment_rejects_stale_revision(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(monkeypatch)
    comment = service.post_comment(task_id="task-1", body="Original text")

    with pytest.raises(ConcurrencyError) as exc:
        service.edit_comment(
            comment.id,
            "Stale edit",
            expected_revision=comment.version + 1,
        )

    assert exc.value.code == "STALE_WRITE"


def test_edit_comment_rejects_non_author(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(monkeypatch)
    comment = service.post_comment(task_id="task-1", body="Original text")

    other_service = _make_service(monkeypatch, user_id="user-2", username="planner", display_name="Project Planner")
    other_service._comment_repo = service._comment_repo

    from src.core.platform.common.exceptions import OperationNotPermittedError

    with pytest.raises(OperationNotPermittedError):
        other_service.edit_comment(comment.id, "Hijacked text")


def test_edit_comment_rejects_deleted_comment(monkeypatch: pytest.MonkeyPatch):
    from src.core.platform.common.exceptions import BusinessRuleError

    service = _make_service(monkeypatch)
    comment = service.post_comment(task_id="task-1", body="Original text")
    service.delete_comment(comment.id)

    with pytest.raises(BusinessRuleError):
        service.edit_comment(comment.id, "Edit after delete")


def test_delete_comment_is_soft_and_idempotent(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(monkeypatch)
    comment = service.post_comment(task_id="task-1", body="Will be removed")

    deleted = service.delete_comment(
        comment.id,
        expected_revision=comment.version,
        reason="Contains superseded instructions",
    )
    assert deleted.is_deleted is True
    assert deleted.deleted_at is not None
    assert deleted.body == "Will be removed"  # original text preserved for audit, masked only at serialization
    assert deleted.deleted_by_user_id == "user-1"
    assert deleted.deletion_reason == "Contains superseded instructions"

    deleted_again = service.delete_comment(comment.id)
    assert deleted_again.deleted_at == deleted.deleted_at


def test_post_comment_with_parent_creates_reply_thread(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(monkeypatch)
    root = service.post_comment(task_id="task-1", body="Root comment")

    reply = service.post_comment(task_id="task-1", body="Reply comment", parent_comment_id=root.id)

    assert reply.parent_comment_id == root.id
    assert reply.is_reply is True
    assert root.is_reply is False


def test_post_comment_rejects_parent_from_different_task(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(
        monkeypatch,
    )
    service._task_repo = _FakeTaskRepo(
        {
            "task-1": SimpleNamespace(id="task-1", project_id="proj-1"),
            "task-2": SimpleNamespace(id="task-2", project_id="proj-1"),
        }
    )
    root = service.post_comment(task_id="task-1", body="Root on task 1")

    with pytest.raises(NotFoundError):
        service.post_comment(task_id="task-2", body="Reply from wrong task", parent_comment_id=root.id)


def test_react_and_remove_reaction_round_trip(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(monkeypatch)
    comment = service.post_comment(task_id="task-1", body="React to me")

    reacted = service.react_to_comment(comment.id, "👍")
    assert reacted.reactions == {"👍": ["user-1"]}

    reacted_twice = service.react_to_comment(comment.id, "👍")
    assert reacted_twice.reactions == {"👍": ["user-1"]}

    cleared = service.remove_reaction(comment.id, "👍")
    assert cleared.reactions == {}


def test_react_to_deleted_comment_raises(monkeypatch: pytest.MonkeyPatch):
    from src.core.platform.common.exceptions import BusinessRuleError

    service = _make_service(monkeypatch)
    comment = service.post_comment(task_id="task-1", body="Will be removed")
    service.delete_comment(comment.id)

    with pytest.raises(BusinessRuleError):
        service.react_to_comment(comment.id, "👍")
