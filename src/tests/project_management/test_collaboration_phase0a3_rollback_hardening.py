"""Phase 0A.3 tests — Collaboration rollback hardening
(docs/pm_modernization/CQRS/project_management_cqrs_existing_state_audit.md, §18 Phase 0A.3).

P44B converged all 6 durable `TaskComment` command methods onto a canonical
`CollaborationUnitOfWork` (fresh session per transaction, atomic mutation + EnterpriseAudit +
typed DomainEvent + single commit) and deleted `collaboration_changed` -- the durable sections
below are rewritten accordingly: rollback is now proved via the repository CLASS (since each
command opens its own fresh session/repo instance, unlike the old shared-session repo instance)
and via ViewInvalidation hints (replacing the deleted legacy Signal's "zero emitted" assertions).
`touch_task_presence`/`clear_task_presence` are untouched by P44B (P44A already converged presence
onto its own, deliberately UoW-less, ViewInvalidation-only transport) -- their sections below are
unchanged from the original phase.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from src.core.modules.project_management.application.collaboration.event_handlers.view_invalidation import (
    TASK_COMMENT_CATEGORY,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.collaboration.collaboration import (
    SqlAlchemyTaskCommentRepository,
)


class _Boom(RuntimeError):
    """Distinguishable forced-failure marker, so a test can never accidentally pass by
    catching some other, unrelated exception."""


def _boom(*_args, **_kwargs):
    raise _Boom("forced failure for Phase 0A.3 rollback test")


def _make_task(services):
    project = services["project_service"].create_project("Collaboration Rollback Project")
    task = services["task_service"].create_task(
        project.id,
        "Collaboration Rollback Task",
        start_date=date(2026, 3, 2),
        duration_days=3,
    )
    return task


def _spy_hints(services):
    hints: list = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )
    return hints


def _comment_hints(hints):
    return [h for h in hints if h.category == TASK_COMMENT_CATEGORY]


# ---------------------------------------------------------------------------
# post_comment — the full required-tests matrix.
# ---------------------------------------------------------------------------


def test_post_comment_repository_failure_rolls_back_with_no_partial_row(services, monkeypatch):
    collaboration = services["collaboration_service"]
    task = _make_task(services)
    hints = _spy_hints(services)
    monkeypatch.setattr(SqlAlchemyTaskCommentRepository, "add", _boom)

    with pytest.raises(_Boom):
        collaboration.post_comment(task_id=task.id, body="Hello")

    monkeypatch.undo()
    assert collaboration._comment_repo.list_by_task(task.id) == []
    assert _comment_hints(hints) == []


def test_post_comment_commit_failure_rolls_back_with_no_partial_row(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    collaboration = services["collaboration_service"]
    task = _make_task(services)
    hints = _spy_hints(services)
    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    with pytest.raises(_Boom):
        collaboration.post_comment(task_id=task.id, body="Hello")

    monkeypatch.undo()
    assert collaboration._comment_repo.list_by_task(task.id) == []
    assert _comment_hints(hints) == []


def test_session_remains_usable_after_post_comment_repository_failure(services, monkeypatch):
    collaboration = services["collaboration_service"]
    task = _make_task(services)
    monkeypatch.setattr(SqlAlchemyTaskCommentRepository, "add", _boom)
    with pytest.raises(_Boom):
        collaboration.post_comment(task_id=task.id, body="Hello")
    monkeypatch.undo()

    created = collaboration.post_comment(task_id=task.id, body="Hello again")

    assert created is not None
    assert [c.id for c in collaboration._comment_repo.list_by_task(task.id)] == [created.id]


def test_post_comment_successful_write_produces_a_durable_hint(services):
    collaboration = services["collaboration_service"]
    task = _make_task(services)
    hints = _spy_hints(services)

    created = collaboration.post_comment(task_id=task.id, body="Hello")

    assert created is not None
    assert created.body == "Hello"
    assert [c.id for c in collaboration._comment_repo.list_by_task(task.id)] == [created.id]
    assert len(_comment_hints(hints)) == 2, "task-scoped + org-wide workspace target"


# ---------------------------------------------------------------------------
# mark_task_mentions_read — repository-failure and commit-failure rollback,
# covering the mutate-in-a-loop shape.
# ---------------------------------------------------------------------------


def test_mark_task_mentions_read_rolls_back_on_repository_failure(services, monkeypatch):
    collaboration = services["collaboration_service"]
    task = _make_task(services)
    principal = services["user_session"].principal
    mention_username = principal.username
    comment = collaboration.post_comment(task_id=task.id, body=f"Hey @{mention_username}")
    hints = _spy_hints(services)
    monkeypatch.setattr(SqlAlchemyTaskCommentRepository, "update", _boom)

    with pytest.raises(_Boom):
        collaboration.mark_task_mentions_read(task.id)

    monkeypatch.undo()
    reloaded = collaboration._comment_repo.get(comment.id)
    assert reloaded.read_by_user_ids == []
    assert _comment_hints(hints) == []


def test_mark_task_mentions_read_rolls_back_on_commit_failure_and_session_stays_usable(
    services, monkeypatch
):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    collaboration = services["collaboration_service"]
    task = _make_task(services)
    principal = services["user_session"].principal
    mention_username = principal.username
    comment = collaboration.post_comment(task_id=task.id, body=f"Hey @{mention_username}")
    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    with pytest.raises(_Boom):
        collaboration.mark_task_mentions_read(task.id)

    monkeypatch.undo()
    reloaded = collaboration._comment_repo.get(comment.id)
    assert reloaded.read_by_user_ids == []

    collaboration.mark_task_mentions_read(task.id)
    reloaded_again = collaboration._comment_repo.get(comment.id)
    assert principal.user_id in reloaded_again.read_by_user_ids


# ---------------------------------------------------------------------------
# edit_comment / delete_comment / react_to_comment / remove_reaction —
# repository-failure rollback for each.
# ---------------------------------------------------------------------------


def test_edit_comment_rolls_back_on_repository_failure(services, monkeypatch):
    collaboration = services["collaboration_service"]
    task = _make_task(services)
    comment = collaboration.post_comment(task_id=task.id, body="Original body")
    monkeypatch.setattr(SqlAlchemyTaskCommentRepository, "update", _boom)

    with pytest.raises(_Boom):
        collaboration.edit_comment(comment.id, "Changed body")

    monkeypatch.undo()
    reloaded = collaboration._comment_repo.get(comment.id)
    assert reloaded.body == "Original body"


def test_delete_comment_rolls_back_on_repository_failure(services, monkeypatch):
    collaboration = services["collaboration_service"]
    task = _make_task(services)
    comment = collaboration.post_comment(task_id=task.id, body="Do not delete me")
    monkeypatch.setattr(SqlAlchemyTaskCommentRepository, "update", _boom)

    with pytest.raises(_Boom):
        collaboration.delete_comment(comment.id)

    monkeypatch.undo()
    reloaded = collaboration._comment_repo.get(comment.id)
    assert reloaded.is_deleted is False


def test_react_to_comment_rolls_back_on_repository_failure(services, monkeypatch):
    collaboration = services["collaboration_service"]
    task = _make_task(services)
    comment = collaboration.post_comment(task_id=task.id, body="React to me")
    monkeypatch.setattr(SqlAlchemyTaskCommentRepository, "update", _boom)

    with pytest.raises(_Boom):
        collaboration.react_to_comment(comment.id, "👍")

    monkeypatch.undo()
    reloaded = collaboration._comment_repo.get(comment.id)
    assert reloaded.reactions == {}


def test_remove_reaction_rolls_back_on_repository_failure(services, monkeypatch):
    collaboration = services["collaboration_service"]
    task = _make_task(services)
    comment = collaboration.post_comment(task_id=task.id, body="Unreact from me")
    collaboration.react_to_comment(comment.id, "👍")
    monkeypatch.setattr(SqlAlchemyTaskCommentRepository, "update", _boom)

    with pytest.raises(_Boom):
        collaboration.remove_reaction(comment.id, "👍")

    monkeypatch.undo()
    reloaded = collaboration._comment_repo.get(comment.id)
    assert "👍" in reloaded.reactions


# ---------------------------------------------------------------------------
# touch_task_presence / clear_task_presence — repository-failure and
# commit-failure rollback.
# ---------------------------------------------------------------------------


def _presence_count(collaboration, task_id):
    since = datetime.now(timezone.utc) - timedelta(days=1)
    return len(collaboration._presence_repo.list_recent_for_tasks([task_id], since=since))


def test_touch_task_presence_rolls_back_on_repository_failure(services, monkeypatch):
    collaboration = services["collaboration_service"]
    task = _make_task(services)
    before = _presence_count(collaboration, task.id)
    monkeypatch.setattr(collaboration._presence_repo, "touch", _boom)

    with pytest.raises(_Boom):
        collaboration.touch_task_presence(task.id)

    monkeypatch.undo()
    assert _presence_count(collaboration, task.id) == before


def test_touch_task_presence_rolls_back_on_commit_failure_and_session_stays_usable(
    services, monkeypatch
):
    collaboration = services["collaboration_service"]
    task = _make_task(services)
    before = _presence_count(collaboration, task.id)
    monkeypatch.setattr(services["session"], "commit", _boom)

    with pytest.raises(_Boom):
        collaboration.touch_task_presence(task.id)

    monkeypatch.undo()
    assert _presence_count(collaboration, task.id) == before

    collaboration.touch_task_presence(task.id)
    assert _presence_count(collaboration, task.id) == before + 1


def test_clear_task_presence_rolls_back_on_repository_failure(services, monkeypatch):
    collaboration = services["collaboration_service"]
    task = _make_task(services)
    collaboration.touch_task_presence(task.id)
    before = _presence_count(collaboration, task.id)
    assert before > 0
    monkeypatch.setattr(collaboration._presence_repo, "clear", _boom)

    with pytest.raises(_Boom):
        collaboration.clear_task_presence(task.id)

    monkeypatch.undo()
    assert _presence_count(collaboration, task.id) == before
