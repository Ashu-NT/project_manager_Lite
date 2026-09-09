from __future__ import annotations

import ast
import glob

from src.core.modules.project_management.application.collaboration.event_handlers.view_invalidation import (
    TASK_COMMENT_CATEGORY,
    TASK_PRESENCE_CATEGORY,
    TASK_PRESENCE_SCOPE_CODE,
)


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
# Ephemeral presence producers never touch the durable comment category
# ---------------------------------------------------------------------------


def test_touch_task_presence_produces_zero_durable_comment_hints(services):
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


def test_touch_task_presence_does_not_emit_a_task_view_invalidation_hint(services):
    """Presence is ephemeral and ViewInvalidation-only; it must never produce a Task-category
    hint -- that category is reserved for genuine Task aggregate mutations."""
    from src.core.modules.project_management.application.tasks.event_handlers.view_invalidation import (
        TASK_CATEGORY,
    )

    _, task = _setup(services)
    hints = _spy_hints(services)
    services["collaboration_service"].touch_task_presence(task.id, activity="reviewing")
    assert [h for h in hints if h.category == TASK_CATEGORY] == []


def test_presence_producers_source_never_names_collaboration_changed_or_tasks_changed():
    """Source-level guard: proves the ephemeral presence producer never references a legacy
    signal or the canonical event/dispatch machinery."""
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
# Presence uses a direct, scoped ViewInvalidation notify, not a DomainEvent
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
# No durable refresh amplification from presence, including under a storm
# ---------------------------------------------------------------------------


def test_repeated_presence_touches_never_trigger_a_durable_collaboration_signal(services):
    """10 repeated touches: the durable-refresh hint count must stay zero; only the lightweight
    presence-hint count grows."""
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
# Durable comment operations still cause the durable refresh
# ---------------------------------------------------------------------------
# See test_p44b_collaboration_comment_full_modernization.py for the durable-refresh proof.


def test_post_comment_does_not_produce_a_presence_hint(services):
    """A durable mutation must not accidentally route through the presence transport."""
    _, task = _setup(services)
    hints = _spy_hints(services)

    services["collaboration_service"].post_comment(task_id=task.id, body="No presence hint here")

    assert _presence_hints(hints) == []


# ---------------------------------------------------------------------------
# Enterprise audit separation
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
# Multi-user / same-user semantics
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
# Approval infrastructure baseline unchanged
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
    assert hits == set()
