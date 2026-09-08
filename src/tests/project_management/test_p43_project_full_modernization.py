from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.modules.project_management.application.projects.event_handlers.view_invalidation import (
    PROJECT_CATEGORY,
    PROJECT_DETAIL_SCOPE_CODE,
    PROJECT_LIST_SCOPE_CODE,
    build_project_view_invalidation_handler,
)
from src.core.modules.project_management.application.projects.project_events import (
    ProjectCreated,
    ProjectProfileUpdated,
    ProjectRemoved,
    ProjectStatusChanged,
)
from src.core.modules.project_management.application.resources.project_resource_events import (
    ProjectResourceAssignmentChanged,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events


def test_legacy_project_signal_field_is_deleted():
    assert not hasattr(domain_events, "project_changed")


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


def test_project_created_maps_to_list_target_only():
    channel = _fake_channel()
    handler = build_project_view_invalidation_handler(channel)
    handler(
        ProjectCreated(
            tenant_id="t1", organization_id="o1", project_id="p1",
            occurred_at=datetime.now(timezone.utc),
        ),
        DomainEventContext(correlation_id="c1"),
    )
    assert {h.scope_code for h in channel.notified} == {PROJECT_LIST_SCOPE_CODE}
    assert all(h.category == PROJECT_CATEGORY for h in channel.notified)


@pytest.mark.parametrize(
    "event",
    [
        ProjectProfileUpdated(
            tenant_id="t1", organization_id="o1", project_id="p1",
            occurred_at=datetime.now(timezone.utc),
        ),
        ProjectStatusChanged(
            tenant_id="t1", organization_id="o1", project_id="p1",
            status=ProjectStatus.ACTIVE, occurred_at=datetime.now(timezone.utc),
        ),
        ProjectRemoved(
            tenant_id="t1", organization_id="o1", project_id="p1",
            occurred_at=datetime.now(timezone.utc),
        ),
    ],
)
def test_profile_status_and_removed_map_to_both_targets(event):
    channel = _fake_channel()
    handler = build_project_view_invalidation_handler(channel)
    handler(event, DomainEventContext(correlation_id="c1"))
    scope_codes = {h.scope_code for h in channel.notified}
    assert scope_codes == {PROJECT_LIST_SCOPE_CODE, PROJECT_DETAIL_SCOPE_CODE}
    assert all(h.entity_id == "p1" for h in channel.notified)


def test_project_resource_assignment_changed_maps_to_detail_only():
    channel = _fake_channel()
    handler = build_project_view_invalidation_handler(channel)
    handler(
        ProjectResourceAssignmentChanged(
            tenant_id="t1", organization_id="o1", project_id="p1",
            occurred_at=datetime.now(timezone.utc),
        ),
        DomainEventContext(correlation_id="c1"),
    )
    assert {h.scope_code for h in channel.notified} == {PROJECT_DETAIL_SCOPE_CODE}


def test_dedupe_by_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_project_view_invalidation_handler(channel)
    event = ProjectProfileUpdated(
        tenant_id="t1", organization_id="o1", project_id="p1",
        occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="same-tx"))
    handler(event, DomainEventContext(correlation_id="same-tx"))
    assert len(channel.notified) == 2, "two distinct targets, each coalesced within one tx"

    handler(event, DomainEventContext(correlation_id="next-tx"))
    assert len(channel.notified) == 4, "a new transaction is never coalesced with the previous one"


# ---------------------------------------------------------------------------
# Real producer path -- create/set_status/update/delete, converged onto ProjectUnitOfWork
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


def _project_hints(hints):
    return [h for h in hints if h.category == PROJECT_CATEGORY]


def _audit_rows_for(services, entity_id: str):
    from sqlalchemy import select

    from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
        AuditEntryORM,
    )

    return services["session"].execute(
        select(AuditEntryORM).where(AuditEntryORM.entity_id == entity_id)
    ).scalars().all()


def test_create_produces_list_hint_and_atomic_audit_for_project_and_financial_profile(services):
    hints = _spy_hints(services)

    project = services["project_service"].create_project("P43 project", "")

    project_hints = _project_hints(hints)
    assert {h.scope_code for h in project_hints} == {PROJECT_LIST_SCOPE_CODE}

    rows = _audit_rows_for(services, project.id)
    assert [row.operation for row in rows] == ["create"]


def test_set_status_closes_the_silent_notification_gap(services):
    """The P40A-discovered bug: before P43, `set_status` persisted the status change but emitted
    zero `project_changed` -- every consumer stayed stale. This proves the fix end to end: the
    status persists, a typed `ProjectStatusChanged` is recorded, and both the list and detail
    ViewInvalidation targets fire -- a consumer subscribed to either would now actually refresh."""
    project = services["project_service"].create_project("P43 status project", "")
    hints = _spy_hints(services)

    updated = services["project_service"].set_status(project.id, ProjectStatus.ACTIVE)

    assert updated.status == ProjectStatus.ACTIVE
    reloaded = services["project_service"].get_project(project.id)
    assert reloaded.status == ProjectStatus.ACTIVE

    project_hints = _project_hints(hints)
    assert {h.scope_code for h in project_hints} == {PROJECT_LIST_SCOPE_CODE, PROJECT_DETAIL_SCOPE_CODE}
    assert all(h.entity_id == project.id for h in project_hints)

    rows = _audit_rows_for(services, project.id)
    assert "update" in [row.operation for row in rows], (
        "set_status previously had zero EnterpriseAudit coverage -- now atomic with the mutation"
    )


def test_update_produces_hints_for_profile_change(services):
    project = services["project_service"].create_project("P43 update project", "")
    hints = _spy_hints(services)

    updated = services["project_service"].update_project(project.id, name="P43 update project V2")

    project_hints = _project_hints(hints)
    assert {h.scope_code for h in project_hints} == {PROJECT_LIST_SCOPE_CODE, PROJECT_DETAIL_SCOPE_CODE}
    assert updated.name == "P43 update project V2"


def test_update_that_also_changes_status_emits_both_facts(services):
    project = services["project_service"].create_project("P43 dual-fact project", "")
    hints = _spy_hints(services)

    services["project_service"].update_project(
        project.id, name="P43 dual-fact project V2", status=ProjectStatus.ON_HOLD
    )

    project_hints = _project_hints(hints)
    # ProjectProfileUpdated and ProjectStatusChanged both map to the same two targets, deduped
    # within the one transaction -- so this still proves both facts were genuinely recorded via
    # the audit trail rather than merely asserting hint count.
    assert {h.scope_code for h in project_hints} == {PROJECT_LIST_SCOPE_CODE, PROJECT_DETAIL_SCOPE_CODE}
    reloaded = services["project_service"].get_project(project.id)
    assert reloaded.status == ProjectStatus.ON_HOLD


def test_delete_produces_hints_and_atomic_audit(services):
    project = services["project_service"].create_project("P43 delete project", "")
    hints = _spy_hints(services)

    services["project_service"].delete_project(project.id)

    project_hints = _project_hints(hints)
    assert {h.scope_code for h in project_hints} == {PROJECT_LIST_SCOPE_CODE, PROJECT_DETAIL_SCOPE_CODE}
    assert services["project_service"].get_project(project.id) is None

    rows = _audit_rows_for(services, project.id)
    assert "delete" in [row.operation for row in rows]


def test_project_resource_add_produces_detail_hint_only(services):
    project = services["project_service"].create_project("P43 pr project", "")
    resource = services["resource_service"].create_resource("P43 PR Resource", "Developer")
    hints = _spy_hints(services)

    services["project_resource_service"].add_to_project(project.id, resource.id)

    project_hints = _project_hints(hints)
    assert {h.scope_code for h in project_hints} == {PROJECT_DETAIL_SCOPE_CODE}


# ---------------------------------------------------------------------------
# Audit failure rollback -- including set_status, previously the weakest path
# ---------------------------------------------------------------------------


def test_audit_failure_rolls_back_create_permanently(services, monkeypatch):
    hints = _spy_hints(services)

    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    def _boom(self, **kwargs):
        raise RuntimeError("simulated enterprise audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    with pytest.raises(RuntimeError):
        services["project_service"].create_project("Should never persist", "")

    assert _project_hints(hints) == []
    assert services["project_service"].list_projects() == []


def test_audit_failure_rolls_back_set_status_permanently(services, monkeypatch):
    """§18/§19: `set_status` previously had the weakest audit path of all Project mutations
    (none at all) -- this proves it now rolls back exactly like every other command."""
    project = services["project_service"].create_project("P43 status rollback project", "")
    hints = _spy_hints(services)

    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    def _boom(self, **kwargs):
        raise RuntimeError("simulated enterprise audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    with pytest.raises(RuntimeError):
        services["project_service"].set_status(project.id, ProjectStatus.COMPLETED)

    assert _project_hints(hints) == []
    reloaded = services["project_service"].get_project(project.id)
    assert reloaded.status == ProjectStatus.PLANNED


def test_transactional_handler_failure_rolls_back_and_never_publishes(services):
    """§54: a typed Project transactional handler raising must roll back the whole transaction
    and produce zero postcommit ViewInvalidation, exercising the real, shared
    `platform_transactional_dispatcher` (not a fake one) through Project's own wiring."""
    hints = _spy_hints(services)

    dispatcher = services["project_service"]._uow_factory._transactional_dispatcher

    def _raising_handler(event, uow) -> None:
        raise RuntimeError("simulated transactional handler failure")

    dispatcher.subscribe(ProjectCreated, _raising_handler)

    with pytest.raises(RuntimeError):
        services["project_service"].create_project("Should never persist either", "")

    assert _project_hints(hints) == []
    assert services["project_service"].list_projects() == []


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_stale_update_raises_and_produces_zero_hints_and_zero_write(services):
    project = services["project_service"].create_project("P43 stale project", "")
    hints = _spy_hints(services)

    with pytest.raises(ConcurrencyError):
        services["project_service"].update_project(
            project.id, expected_version=project.version + 1, name="Should not apply"
        )

    assert _project_hints(hints) == []
    reloaded = services["project_service"].get_project(project.id)
    assert reloaded.name == "P43 stale project"


def test_concurrent_set_status_second_writer_gets_canonical_concurrency_error(services):
    """§21/§57: `set_status` has no `expected_version` guard of its own visibility, but the repo
    always performs a version-checked conditional update -- two genuinely independent reads/writes
    on the same row must not silently overwrite each other."""
    project = services["project_service"].create_project("P43 concurrent status project", "")

    winner = services["project_service"].get_project(project.id)
    loser = services["project_service"].get_project(project.id)
    assert winner.version == loser.version

    services["project_service"].set_status(
        winner.id, ProjectStatus.ACTIVE, expected_version=winner.version
    )

    with pytest.raises(ConcurrencyError):
        services["project_service"].set_status(
            loser.id, ProjectStatus.ON_HOLD, expected_version=loser.version
        )

    reloaded = services["project_service"].get_project(project.id)
    assert reloaded.status == ProjectStatus.ACTIVE


def test_duplicate_name_rejected_with_zero_hints(services):
    services["project_service"].create_project("P43 Duplicate Name", "")
    hints = _spy_hints(services)

    with pytest.raises(ValidationError):
        services["project_service"].create_project("P43 Duplicate Name", "")

    assert _project_hints(hints) == []


# ---------------------------------------------------------------------------
# Cross-organization ownership
# ---------------------------------------------------------------------------


def test_set_status_for_unknown_project_is_rejected_with_zero_write(services):
    with pytest.raises(NotFoundError):
        services["project_service"].set_status("not-a-real-project-id", ProjectStatus.ACTIVE)


# ---------------------------------------------------------------------------
# Approval bridge unaffected
# ---------------------------------------------------------------------------


def test_approval_post_commit_event_bridge_is_unaffected_by_project_modernization():
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
