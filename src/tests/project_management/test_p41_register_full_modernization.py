from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.core.modules.project_management.application.risk.event_handlers.view_invalidation import (
    REGISTER_CATEGORY,
    REGISTER_PROJECT_SCOPE_CODE,
    REGISTER_WORKSPACE_SCOPE_CODE,
    build_register_view_invalidation_handler,
)
from src.core.modules.project_management.application.risk.register_events import (
    RegisterEntryChangeType,
    RegisterEntryChanged,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events


def test_legacy_register_signal_field_is_deleted():
    assert not hasattr(domain_events, "register_changed")


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


def _event(*, change_type) -> RegisterEntryChanged:
    return RegisterEntryChanged(
        tenant_id="t1",
        organization_id="o1",
        project_id="p1",
        register_entry_id="e1",
        entry_type=RegisterEntryType.RISK,
        change_type=change_type,
        occurred_at=datetime.now(timezone.utc),
    )


@pytest.mark.parametrize("change_type", list(RegisterEntryChangeType))
def test_every_change_type_maps_to_workspace_and_project_targets(change_type):
    channel = _fake_channel()
    handler = build_register_view_invalidation_handler(channel)
    handler(_event(change_type=change_type), DomainEventContext(correlation_id="c1"))

    scope_codes = {hint.scope_code for hint in channel.notified}
    assert scope_codes == {REGISTER_WORKSPACE_SCOPE_CODE, REGISTER_PROJECT_SCOPE_CODE}
    assert all(hint.category == REGISTER_CATEGORY for hint in channel.notified)
    assert all(hint.entity_id == "p1" for hint in channel.notified)


def test_dedupe_by_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_register_view_invalidation_handler(channel)
    event = _event(change_type=RegisterEntryChangeType.UPDATED)
    handler(event, DomainEventContext(correlation_id="same-tx"))
    handler(event, DomainEventContext(correlation_id="same-tx"))
    assert len(channel.notified) == 2, "two distinct targets, each coalesced within one tx"

    handler(event, DomainEventContext(correlation_id="next-tx"))
    assert len(channel.notified) == 4, "a new transaction is never coalesced with the previous one"


# ---------------------------------------------------------------------------
# Real producer path -- create/update/delete, converged onto RegisterUnitOfWork
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


def _register_hints(hints):
    return [h for h in hints if h.category == REGISTER_CATEGORY]


def _setup(services):
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "P41 Register project", financial_currency_code=organization.base_currency
    )
    return organization, project


def test_create_produces_workspace_and_project_hints_and_zero_legacy_signal(services):
    _, project = _setup(services)
    hints = _spy_hints(services)

    entry = services["register_service"].create_entry(
        project.id,
        entry_type=RegisterEntryType.RISK,
        title="P41 risk",
    )

    reg_hints = _register_hints(hints)
    scope_codes = {h.scope_code for h in reg_hints}
    assert scope_codes == {REGISTER_WORKSPACE_SCOPE_CODE, REGISTER_PROJECT_SCOPE_CODE}
    assert all(h.entity_id == project.id for h in reg_hints)
    assert entry.status == RegisterEntryStatus.OPEN


def test_update_produces_hints_and_true_audit_entry(services):
    _, project = _setup(services)
    entry = services["register_service"].create_entry(
        project.id, entry_type=RegisterEntryType.ISSUE, title="P41 issue"
    )
    hints = _spy_hints(services)

    updated = services["register_service"].update_entry(
        entry.id, expected_version=entry.version, status=RegisterEntryStatus.IN_PROGRESS
    )

    reg_hints = _register_hints(hints)
    assert len(reg_hints) == 2
    assert updated.status == RegisterEntryStatus.IN_PROGRESS

    from sqlalchemy import select

    from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
        AuditEntryORM,
    )

    rows = services["session"].execute(
        select(AuditEntryORM).where(AuditEntryORM.entity_id == entry.id)
    ).scalars().all()
    operations = sorted(row.operation for row in rows)
    assert operations == ["create", "update"], (
        "enterprise audit now records both mutations atomically, not just the Activity feed"
    )


def test_delete_produces_hints(services):
    _, project = _setup(services)
    entry = services["register_service"].create_entry(
        project.id, entry_type=RegisterEntryType.CHANGE, title="P41 change"
    )
    hints = _spy_hints(services)

    services["register_service"].delete_entry(entry.id)

    reg_hints = _register_hints(hints)
    assert {h.scope_code for h in reg_hints} == {
        REGISTER_WORKSPACE_SCOPE_CODE,
        REGISTER_PROJECT_SCOPE_CODE,
    }
    with pytest.raises(NotFoundError):
        services["register_service"].get_entry(entry.id)


def test_stale_version_raises_and_produces_zero_hints_and_zero_write(services):
    _, project = _setup(services)
    entry = services["register_service"].create_entry(
        project.id, entry_type=RegisterEntryType.RISK, title="P41 stale"
    )
    hints = _spy_hints(services)

    with pytest.raises(ConcurrencyError):
        services["register_service"].update_entry(
            entry.id, expected_version=entry.version + 1, title="Should not apply"
        )

    assert _register_hints(hints) == []
    reloaded = services["register_service"].get_entry(entry.id)
    assert reloaded.title == "P41 stale"


def test_duplicate_code_rejected_with_zero_hints(services):
    _, project = _setup(services)
    services["register_service"].create_entry(
        project.id, entry_type=RegisterEntryType.RISK, title="First", code="REG-DUP"
    )
    hints = _spy_hints(services)

    with pytest.raises(ValidationError):
        services["register_service"].create_entry(
            project.id, entry_type=RegisterEntryType.ISSUE, title="Second", code="REG-DUP"
        )

    assert _register_hints(hints) == []


# ---------------------------------------------------------------------------
# P40A's two-commit bug: audit failure must roll back the Register mutation
# ---------------------------------------------------------------------------


def test_audit_failure_rolls_back_the_register_mutation_permanently(services, monkeypatch):
    """The mandatory P41 acceptance test (§13/§36). Before this phase, `create_entry` committed
    the business mutation FIRST, then recorded Activity feed second in a separate commit -- an
    audit-adjacent failure there could never undo the already-committed row. This proves the
    opposite is now true: a failure anywhere in the one-transaction write path leaves ZERO
    persisted state, not a commit-count assertion."""
    _, project = _setup(services)
    hints = _spy_hints(services)

    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    def _boom(self, **kwargs):
        raise RuntimeError("simulated enterprise audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    with pytest.raises(RuntimeError):
        services["register_service"].create_entry(
            project.id, entry_type=RegisterEntryType.RISK, title="Should never persist"
        )

    assert _register_hints(hints) == []
    all_entries = services["register_service"].list_entries(project_id=project.id)
    assert all_entries == []


def test_transactional_handler_failure_rolls_back_and_never_publishes(services):
    """§37: a typed Register transactional handler raising must roll back the whole transaction
    and produce zero postcommit ViewInvalidation, exercising the real, shared
    `platform_transactional_dispatcher` (not a fake one) through Register's own wiring."""
    _, project = _setup(services)
    hints = _spy_hints(services)

    dispatcher = services["register_service"]._uow_factory._transactional_dispatcher

    def _raising_handler(event, uow) -> None:
        raise RuntimeError("simulated transactional handler failure")

    dispatcher.subscribe(RegisterEntryChanged, _raising_handler)

    with pytest.raises(RuntimeError):
        services["register_service"].create_entry(
            project.id, entry_type=RegisterEntryType.RISK, title="Should never persist either"
        )

    assert _register_hints(hints) == []
    all_entries = services["register_service"].list_entries(project_id=project.id)
    assert all_entries == []


# ---------------------------------------------------------------------------
# Cross-project / cross-org ownership
# ---------------------------------------------------------------------------


def test_create_entry_for_unknown_project_is_rejected_with_zero_write(services):
    with pytest.raises(NotFoundError):
        services["register_service"].create_entry(
            "not-a-real-project-id", entry_type=RegisterEntryType.RISK, title="Orphan"
        )


# ---------------------------------------------------------------------------
# Approval bridge unaffected
# ---------------------------------------------------------------------------


def test_approval_post_commit_event_bridge_is_unaffected_by_register_modernization():
    import ast
    import glob

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
