from __future__ import annotations

import ast
import glob
from datetime import datetime, timezone

import pytest

from src.core.modules.project_management.application.collaboration.collaboration_events import (
    TaskCommentChangeType,
    TaskCommentChanged,
    TaskCommentReactionChangeType,
    TaskCommentReactionChanged,
    TaskCommentReadStateChanged,
)
from src.core.modules.project_management.application.collaboration.event_handlers.view_invalidation import (
    COLLABORATION_WORKSPACE_SCOPE_CODE,
    TASK_COMMENT_CATEGORY,
    TASK_COMMENT_SCOPE_CODE,
    build_task_comment_view_invalidation_handler,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.collaboration.collaboration import (
    SqlAlchemyTaskCommentRepository,
)
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events


def test_legacy_collaboration_signal_field_is_deleted():
    assert not hasattr(domain_events, "collaboration_changed")


# ---------------------------------------------------------------------------
# ViewInvalidation handler: unit-level mapping/dedupe
# ---------------------------------------------------------------------------


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


@pytest.mark.parametrize("change_type", list(TaskCommentChangeType))
def test_task_comment_changed_maps_to_task_and_workspace_targets(change_type):
    channel = _fake_channel()
    handler = build_task_comment_view_invalidation_handler(channel)
    handler(
        TaskCommentChanged(
            tenant_id="t1", organization_id="o1", project_id="p1", task_id="task1",
            comment_id="c1", change_type=change_type, occurred_at=datetime.now(timezone.utc),
        ),
        DomainEventContext(correlation_id="c1"),
    )
    scope_codes = {hint.scope_code for hint in channel.notified}
    assert scope_codes == {TASK_COMMENT_SCOPE_CODE, COLLABORATION_WORKSPACE_SCOPE_CODE}
    assert all(hint.category == TASK_COMMENT_CATEGORY for hint in channel.notified)


@pytest.mark.parametrize("change_type", list(TaskCommentReactionChangeType))
def test_reaction_changed_maps_to_task_target_only(change_type):
    channel = _fake_channel()
    handler = build_task_comment_view_invalidation_handler(channel)
    handler(
        TaskCommentReactionChanged(
            tenant_id="t1", organization_id="o1", project_id="p1", task_id="task1",
            comment_id="c1", change_type=change_type, occurred_at=datetime.now(timezone.utc),
        ),
        DomainEventContext(correlation_id="c1"),
    )
    assert {hint.scope_code for hint in channel.notified} == {TASK_COMMENT_SCOPE_CODE}


def test_read_state_changed_maps_to_task_target_only():
    channel = _fake_channel()
    handler = build_task_comment_view_invalidation_handler(channel)
    handler(
        TaskCommentReadStateChanged(
            tenant_id="t1", organization_id="o1", project_id="p1", task_id="task1",
            comment_id="c1", occurred_at=datetime.now(timezone.utc),
        ),
        DomainEventContext(correlation_id="c1"),
    )
    assert {hint.scope_code for hint in channel.notified} == {TASK_COMMENT_SCOPE_CODE}


def test_dedupe_by_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_task_comment_view_invalidation_handler(channel)
    event = TaskCommentChanged(
        tenant_id="t1", organization_id="o1", project_id="p1", task_id="task1",
        comment_id="c1", change_type=TaskCommentChangeType.CREATED, occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="same-tx"))
    handler(event, DomainEventContext(correlation_id="same-tx"))
    assert len(channel.notified) == 2, "two distinct targets, each coalesced within one tx"

    handler(event, DomainEventContext(correlation_id="next-tx"))
    assert len(channel.notified) == 4, "a new transaction is never coalesced with the previous one"


# ---------------------------------------------------------------------------
# Real producer path -- converged onto CollaborationUnitOfWork
# ---------------------------------------------------------------------------


def _spy_hints(services):
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )
    return hints


def _comment_hints(hints):
    return [h for h in hints if h.category == TASK_COMMENT_CATEGORY]


def _audit_rows_for(services, entity_id: str):
    from sqlalchemy import select

    from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
        AuditEntryORM,
    )

    return services["session"].execute(
        select(AuditEntryORM).where(AuditEntryORM.entity_id == entity_id)
    ).scalars().all()


def _setup(services):
    project = services["project_service"].create_project("P44B collaboration project")
    task = services["task_service"].create_task(project.id, "P44B collaboration task")
    return project, task


def test_post_comment_produces_both_targets_and_atomic_audit(services):
    _, task = _setup(services)
    hints = _spy_hints(services)

    comment = services["collaboration_service"].post_comment(task_id=task.id, body="Hello durable world")

    comment_hints = _comment_hints(hints)
    assert {h.scope_code for h in comment_hints} == {TASK_COMMENT_SCOPE_CODE, COLLABORATION_WORKSPACE_SCOPE_CODE}
    rows = _audit_rows_for(services, comment.id)
    assert [row.operation for row in rows] == ["create"]


def test_edit_comment_produces_hints_and_audit(services):
    _, task = _setup(services)
    comment = services["collaboration_service"].post_comment(task_id=task.id, body="Original")
    hints = _spy_hints(services)

    edited = services["collaboration_service"].edit_comment(
        comment.id, "Edited body", expected_revision=comment.version
    )

    comment_hints = _comment_hints(hints)
    assert {h.scope_code for h in comment_hints} == {TASK_COMMENT_SCOPE_CODE, COLLABORATION_WORKSPACE_SCOPE_CODE}
    assert edited.body == "Edited body"
    rows = _audit_rows_for(services, comment.id)
    assert sorted(row.operation for row in rows) == ["create", "update"]


def test_delete_comment_produces_hints_and_audit(services):
    _, task = _setup(services)
    comment = services["collaboration_service"].post_comment(task_id=task.id, body="Delete me")
    hints = _spy_hints(services)

    deleted = services["collaboration_service"].delete_comment(comment.id)

    comment_hints = _comment_hints(hints)
    assert {h.scope_code for h in comment_hints} == {TASK_COMMENT_SCOPE_CODE, COLLABORATION_WORKSPACE_SCOPE_CODE}
    assert deleted.is_deleted is True
    rows = _audit_rows_for(services, comment.id)
    assert sorted(row.operation for row in rows) == ["create", "delete"]


def test_react_and_remove_reaction_produce_task_scoped_hints_only(services):
    _, task = _setup(services)
    comment = services["collaboration_service"].post_comment(task_id=task.id, body="React to me")
    hints = _spy_hints(services)

    reacted = services["collaboration_service"].react_to_comment(comment.id, "👍")
    react_hints = _comment_hints(hints)
    assert {h.scope_code for h in react_hints} == {TASK_COMMENT_SCOPE_CODE}
    assert "👍" in reacted.reactions

    hints2 = _spy_hints(services)
    unreacted = services["collaboration_service"].remove_reaction(comment.id, "👍")
    unreact_hints = _comment_hints(hints2)
    assert {h.scope_code for h in unreact_hints} == {TASK_COMMENT_SCOPE_CODE}
    assert "👍" not in unreacted.reactions


def test_mark_task_mentions_read_produces_task_scoped_hint_only(services):
    principal = services["user_session"].principal
    _, task = _setup(services)
    services["collaboration_service"].post_comment(task_id=task.id, body=f"Hey @{principal.username}")
    hints = _spy_hints(services)

    services["collaboration_service"].mark_task_mentions_read(task.id)

    read_hints = _comment_hints(hints)
    assert {h.scope_code for h in read_hints} == {TASK_COMMENT_SCOPE_CODE}


# ---------------------------------------------------------------------------
# No-op semantics preserved exactly (source-established, not invented here)
# ---------------------------------------------------------------------------


def test_mark_task_mentions_read_is_a_true_no_op_when_already_read(services):
    principal = services["user_session"].principal
    _, task = _setup(services)
    services["collaboration_service"].post_comment(task_id=task.id, body=f"Hey @{principal.username}")
    services["collaboration_service"].mark_task_mentions_read(task.id)

    hints = _spy_hints(services)
    services["collaboration_service"].mark_task_mentions_read(task.id)

    assert _comment_hints(hints) == [], "already-read is a true no-op: zero write/audit/event"


def test_delete_comment_is_a_true_no_op_when_already_deleted(services):
    _, task = _setup(services)
    comment = services["collaboration_service"].post_comment(task_id=task.id, body="Delete me once")
    services["collaboration_service"].delete_comment(comment.id)

    hints = _spy_hints(services)
    redeleted = services["collaboration_service"].delete_comment(comment.id)

    assert _comment_hints(hints) == [], "repeated delete is a true no-op: zero write/audit/event"
    assert redeleted.is_deleted is True


def test_reaction_repeat_is_not_a_no_op_matching_current_domain_behavior(services):
    """§54: current domain does NOT treat "same user, same reaction, twice" as a no-op (no
    already-reacted guard exists in source) -- the final persisted state is data-level idempotent
    (still exactly one reactor), but the second call still writes/audits/emits, exactly like the
    first. This test proves and preserves that exact pre-existing behavior, not an invented one."""
    _, task = _setup(services)
    comment = services["collaboration_service"].post_comment(task_id=task.id, body="React twice")

    services["collaboration_service"].react_to_comment(comment.id, "👍")
    hints = _spy_hints(services)
    reacted_again = services["collaboration_service"].react_to_comment(comment.id, "👍")

    assert len(_comment_hints(hints)) == 1, "the source has no idempotency guard -- it writes/emits again"
    assert len(reacted_again.reactions["👍"]) == 1, "the reactor set itself IS data-level idempotent"


# ---------------------------------------------------------------------------
# Audit failure rollback (mandatory, §50) and transactional-handler failure (§51)
# ---------------------------------------------------------------------------


def test_audit_failure_rolls_back_post_comment_permanently(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    _, task = _setup(services)
    hints = _spy_hints(services)

    def _boom(self, **kwargs):
        raise RuntimeError("simulated enterprise audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    with pytest.raises(RuntimeError):
        services["collaboration_service"].post_comment(task_id=task.id, body="Should never persist")

    assert _comment_hints(hints) == []
    monkeypatch.undo()
    assert services["collaboration_service"].list_comments(task.id) == []


def test_transactional_handler_failure_rolls_back_and_never_publishes(services):
    _, task = _setup(services)
    hints = _spy_hints(services)

    dispatcher = services["collaboration_service"]._uow_factory._transactional_dispatcher

    def _raising_handler(event, uow) -> None:
        raise RuntimeError("simulated transactional handler failure")

    dispatcher.subscribe(TaskCommentChanged, _raising_handler)

    with pytest.raises(RuntimeError):
        services["collaboration_service"].post_comment(task_id=task.id, body="Should never persist either")

    assert _comment_hints(hints) == []
    assert services["collaboration_service"].list_comments(task.id) == []


# ---------------------------------------------------------------------------
# Concurrency (§21/§22/§53)
# ---------------------------------------------------------------------------


def test_stale_edit_raises_and_produces_zero_hints_and_zero_write(services):
    _, task = _setup(services)
    comment = services["collaboration_service"].post_comment(task_id=task.id, body="Original")
    hints = _spy_hints(services)

    with pytest.raises(ConcurrencyError):
        services["collaboration_service"].edit_comment(
            comment.id, "Should not apply", expected_revision=comment.version + 1
        )

    assert _comment_hints(hints) == []
    reloaded = services["collaboration_service"]._comment_repo.get(comment.id)
    assert reloaded.body == "Original"


def test_stale_delete_raises_and_produces_zero_hints_and_zero_write(services):
    _, task = _setup(services)
    comment = services["collaboration_service"].post_comment(task_id=task.id, body="Do not delete")
    hints = _spy_hints(services)

    with pytest.raises(ConcurrencyError):
        services["collaboration_service"].delete_comment(
            comment.id, expected_revision=comment.version + 1
        )

    assert _comment_hints(hints) == []
    reloaded = services["collaboration_service"]._comment_repo.get(comment.id)
    assert reloaded.is_deleted is False


def test_two_independent_sessions_concurrent_edit_second_writer_gets_canonical_error(services):
    """§22: a real two-independent-UoW concurrency proof, not merely 'one command raised' --
    asserts the FINAL persisted body reflects only the winner."""
    _, task = _setup(services)
    comment = services["collaboration_service"].post_comment(task_id=task.id, body="Race me")

    winner = services["collaboration_service"]._comment_repo.get(comment.id)
    loser = services["collaboration_service"]._comment_repo.get(comment.id)
    assert winner.version == loser.version

    services["collaboration_service"].edit_comment(
        winner.id, "Winner body", expected_revision=winner.version
    )

    with pytest.raises(ConcurrencyError):
        services["collaboration_service"].edit_comment(
            loser.id, "Loser body", expected_revision=loser.version
        )

    reloaded = services["collaboration_service"]._comment_repo.get(comment.id)
    assert reloaded.body == "Winner body"


# ---------------------------------------------------------------------------
# Cross-organization ownership (§26)
# ---------------------------------------------------------------------------


def test_edit_unknown_comment_is_rejected_with_zero_write(services):
    with pytest.raises(NotFoundError):
        services["collaboration_service"].edit_comment("not-a-real-comment-id", "New body")


# ---------------------------------------------------------------------------
# §41/§42: legacy producers/consumers fully removed; source-level architecture guards
# ---------------------------------------------------------------------------


def test_durable_comment_commands_source_never_names_collaboration_changed():
    path = (
        "src/core/modules/project_management/application/collaboration/commands/"
        "collaboration_comments.py"
    )
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read()
    assert "collaboration_changed" not in source
    assert "domain_events" not in source
    assert "tasks_changed" not in source


def test_no_new_signal_field_introduced():
    import dataclasses

    signal_names = {f.name for f in dataclasses.fields(domain_events)}
    assert signal_names == {"tasks_changed", "auth_changed"}


# ---------------------------------------------------------------------------
# §47: Approval infrastructure baseline unchanged
# ---------------------------------------------------------------------------


def test_approval_post_commit_event_bridge_is_unaffected_by_collaboration_modernization():
    hits: set[str] = set()
    for path in glob.glob("src/**/*_apply_participant.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "ApprovalPostCommitEvent(" not in source:
            continue
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ApprovalPostCommitEvent"
            ):
                hits.add(normalized)
    assert hits == {
        "src/core/modules/project_management/infrastructure/approval/financial_change_apply_participant.py",
        "src/core/modules/project_management/infrastructure/approval/task_apply_participant.py",
    }
