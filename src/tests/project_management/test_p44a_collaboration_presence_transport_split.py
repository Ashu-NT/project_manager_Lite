from __future__ import annotations

import ast
import glob

from src.core.modules.project_management.application.collaboration.event_handlers.view_invalidation import (
    TASK_COMMENT_CATEGORY,
    TASK_PRESENCE_CATEGORY,
    TASK_PRESENCE_SCOPE_CODE,
)
from src.core.shared.events.domain_events import domain_events


def _spy_hints(services):
    hints: list = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )
    return hints


def _presence_hints(hints):
    return [h for h in hints if h.category == TASK_PRESENCE_CATEGORY]


def _durable_comment_hints(hints):
    return [h for h in hints if h.category == TASK_COMMENT_CATEGORY]


def _setup(services):
    project = services["project_service"].create_project("P44A collaboration project")
    task = services["task_service"].create_task(project.id, "P44A collaboration task")
    return project, task


# ---------------------------------------------------------------------------
# §22/§24/§46: ephemeral producers must never emit collaboration_changed / tasks_changed
# ---------------------------------------------------------------------------


def test_touch_task_presence_produces_zero_durable_comment_hints(services):
    """P44B deleted `collaboration_changed` entirely -- the durable-side equivalent of this
    check is now "zero TASK_COMMENT_CATEGORY hints", not "zero legacy Signal emissions"."""
    _, task = _setup(services)
    hints = _spy_hints(services)
    services["collaboration_service"].touch_task_presence(task.id, activity="reviewing")
    assert _durable_comment_hints(hints) == []


def test_clear_task_presence_produces_zero_durable_comment_hints(services):
    _, task = _setup(services)
    services["collaboration_service"].touch_task_presence(task.id, activity="reviewing")
    hints = _spy_hints(services)
    services["collaboration_service"].clear_task_presence(task.id)
    assert _durable_comment_hints(hints) == []


def test_touch_task_presence_does_not_emit_tasks_changed(services):
    _, task = _setup(services)
    calls: list[str] = []
    domain_events.tasks_changed.connect(calls.append)
    try:
        services["collaboration_service"].touch_task_presence(task.id, activity="reviewing")
        assert calls == []
    finally:
        domain_events.tasks_changed.disconnect(calls.append)


def test_presence_producers_source_never_names_collaboration_changed_or_tasks_changed():
    """Architecture guard (§46): a source-level check, not just a runtime probe -- proves no
    ephemeral producer can ever be reintroduced to reference either legacy signal."""
    path = (
        "src/core/modules/project_management/application/collaboration/commands/"
        "collaboration_presence.py"
    )
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read()
    assert "collaboration_changed" not in source
    assert "tasks_changed" not in source
    assert "domain_events" not in source
    assert "record_event" not in source
    assert "TransactionalEventDispatcher" not in source
    assert "PostCommitEventPublisher" not in source


# ---------------------------------------------------------------------------
# §10-§15: presence uses a direct, scoped ViewInvalidation notify -- not a DomainEvent
# ---------------------------------------------------------------------------


def test_touch_task_presence_produces_a_scoped_presence_hint(services):
    _, task = _setup(services)
    hints = _spy_hints(services)

    services["collaboration_service"].touch_task_presence(task.id, activity="reviewing")

    presence_hints = _presence_hints(hints)
    assert len(presence_hints) == 1
    assert presence_hints[0].scope_code == TASK_PRESENCE_SCOPE_CODE
    assert presence_hints[0].entity_id == task.id


def test_clear_task_presence_produces_a_scoped_presence_hint(services):
    _, task = _setup(services)
    services["collaboration_service"].touch_task_presence(task.id, activity="reviewing")
    hints = _spy_hints(services)

    services["collaboration_service"].clear_task_presence(task.id)

    presence_hints = _presence_hints(hints)
    assert len(presence_hints) == 1
    assert presence_hints[0].scope_code == TASK_PRESENCE_SCOPE_CODE
    assert presence_hints[0].entity_id == task.id


# ---------------------------------------------------------------------------
# §26/§27/§35/§36: no durable refresh amplification from presence, including under a storm
# ---------------------------------------------------------------------------


def test_repeated_presence_touches_never_trigger_a_durable_collaboration_signal(services):
    """§36: 10 repeated touches -- assert the expensive durable-refresh hint count stays zero,
    not merely the (expected, harmless) lightweight presence-hint count."""
    _, task = _setup(services)
    hints = _spy_hints(services)
    for _ in range(10):
        services["collaboration_service"].touch_task_presence(task.id, activity="reviewing")

    assert _durable_comment_hints(hints) == [], "presence storm must never trigger a durable refresh"
    assert len(_presence_hints(hints)) == 10, "each touch still produces its own presence hint"


def test_clear_presence_causes_zero_durable_collaboration_refresh(services):
    _, task = _setup(services)
    services["collaboration_service"].touch_task_presence(task.id, activity="reviewing")
    hints = _spy_hints(services)
    services["collaboration_service"].clear_task_presence(task.id)
    assert _durable_comment_hints(hints) == []


# ---------------------------------------------------------------------------
# §28: durable comment operations must still cause the currently-required durable refresh
# ---------------------------------------------------------------------------


# P44A-era `test_post_comment_still_emits_collaboration_changed`/
# `test_edit_delete_react_still_emit_collaboration_changed` characterized durable comment
# operations as still using the legacy `collaboration_changed` Signal, which was P44A's own
# deliberate interim state. P44B converged all 6 durable operations onto typed DomainEvents and
# deleted `collaboration_changed` entirely -- see `test_p44b_collaboration_comment_full_
# modernization.py` for the equivalent (and now much more precise) durable-refresh proof.


def test_post_comment_does_not_produce_a_presence_hint(services):
    """A durable mutation must not accidentally route through the presence transport."""
    _, task = _setup(services)
    hints = _spy_hints(services)

    services["collaboration_service"].post_comment(task_id=task.id, body="No presence hint here")

    assert _presence_hints(hints) == []


# ---------------------------------------------------------------------------
# §37: enterprise audit separation
# ---------------------------------------------------------------------------


def test_presence_is_not_enterprise_audited(services):
    from sqlalchemy import select

    from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
        AuditEntryORM,
    )

    _, task = _setup(services)
    before = services["session"].execute(select(AuditEntryORM.id)).scalars().all()

    services["collaboration_service"].touch_task_presence(task.id, activity="reviewing")
    services["collaboration_service"].clear_task_presence(task.id)

    after = services["session"].execute(select(AuditEntryORM.id)).scalars().all()
    assert after == before, "presence keepalive/clear must never flood enterprise audit"


# ---------------------------------------------------------------------------
# §17/§18: multi-user / same-user semantics preserved (not changed by the transport split)
# ---------------------------------------------------------------------------


def test_two_users_can_be_simultaneously_present_without_overwriting_each_other(services):
    from src.core.platform.domain.security.auth.session import UserSessionContext

    _, task = _setup(services)
    services["collaboration_service"].touch_task_presence(task.id, activity="reviewing")

    auth = services["auth_service"]
    auth.register_user("p44a-second-user", "StrongPass123", role_names=["planner"])
    second_session = UserSessionContext()
    second_session.set_principal(
        auth.build_principal(auth.authenticate("p44a-second-user", "StrongPass123"))
    )
    original_session = services["collaboration_service"]._user_session
    services["collaboration_service"]._user_session = second_session
    try:
        services["collaboration_service"].touch_task_presence(task.id, activity="editing")
    finally:
        services["collaboration_service"]._user_session = original_session

    active = services["collaboration_service"].list_task_presence(task.id)
    usernames = {row.username for row in active}
    assert usernames == {"admin", "p44a-second-user"}


# ---------------------------------------------------------------------------
# §42: Approval infrastructure baseline unchanged
# ---------------------------------------------------------------------------


def test_approval_post_commit_event_bridge_is_unaffected_by_collaboration_transport_split():
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


def test_tasks_changed_still_exists_collaboration_changed_now_deleted():
    """P44A did not delete any Signal field -- durable Collaboration commands temporarily
    remained on `collaboration_changed` until P44B, which fully modernized them and deleted the
    field (see `test_p44b_collaboration_comment_full_modernization.py`). `tasks_changed` is
    untouched by both phases and is now the sole remaining PM legacy Signal."""
    assert not hasattr(domain_events, "collaboration_changed")
    assert hasattr(domain_events, "tasks_changed")
