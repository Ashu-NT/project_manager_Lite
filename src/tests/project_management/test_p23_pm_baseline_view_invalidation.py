from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.core.modules.project_management.application.scheduling.baselines.baseline_events import (
    ProjectBaselineApproved,
    ProjectBaselineCreated,
    ProjectBaselineDeleted,
    ProjectBaselineRejected,
    ProjectBaselineSubmitted,
)
from src.core.modules.project_management.application.scheduling.baselines.event_handlers.view_invalidation import (
    BASELINE_CATEGORY,
    BASELINE_PROJECT_SCOPE_CODE,
    build_baseline_view_invalidation_handler,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.events.view_invalidation import ExactResource, ResourceScope

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def _context(correlation_id: str) -> DomainEventContext:
    return DomainEventContext(correlation_id=correlation_id)


def _spy_hints(services):
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(_AnyOrgFilter(), lambda hint: hints.append(hint))
    return hints


def _baseline_hints(hints):
    return [h for h in hints if h.category == BASELINE_CATEGORY]


def _project_with_tasks(services, name: str | None = None):
    project = services["project_service"].create_project(name or _unique("P23 Baseline Project"), "")
    task_service = services["task_service"]
    task_service.create_task(project.id, "Task A", start_date=date(2024, 1, 1), duration_days=2)
    task_service.create_task(project.id, "Task B", start_date=date(2024, 1, 3), duration_days=2)
    return project


# ---------------------------------------------------------------------------
# ViewInvalidation handler: mapping, dedupe (unit-level, no DB)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event_factory",
    [
        lambda now, t, o, p, b: ProjectBaselineCreated(
            tenant_id=t, organization_id=o, project_id=p, baseline_id=b, occurred_at=now
        ),
        lambda now, t, o, p, b: ProjectBaselineSubmitted(
            tenant_id=t, organization_id=o, project_id=p, baseline_id=b, occurred_at=now
        ),
        lambda now, t, o, p, b: ProjectBaselineApproved(
            tenant_id=t, organization_id=o, project_id=p, baseline_id=b,
            superseded_baseline_id=None, occurred_at=now,
        ),
        lambda now, t, o, p, b: ProjectBaselineRejected(
            tenant_id=t, organization_id=o, project_id=p, baseline_id=b, occurred_at=now
        ),
        lambda now, t, o, p, b: ProjectBaselineDeleted(
            tenant_id=t, organization_id=o, project_id=p, baseline_id=b, occurred_at=now
        ),
    ],
)
def test_every_baseline_event_maps_to_the_project_baseline_target(event_factory):
    channel = _fake_channel()
    handler = build_baseline_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    event = event_factory(now, "t1", "o1", "p1", "b1")

    handler(event, _context("tx"))

    assert len(channel.notified) == 1
    hint = channel.notified[0]
    assert hint.category == BASELINE_CATEGORY
    assert hint.scope_code == BASELINE_PROJECT_SCOPE_CODE
    assert isinstance(hint.scope, ResourceScope)
    assert hint.scope.module_code == "project_management"
    assert hint.scope.entity_type == "project"
    assert hint.scope.entity_id == "p1"
    assert hint.entity_id == "p1"


def test_dedupe_by_project_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_baseline_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        ProjectBaselineCreated(tenant_id="t1", organization_id="o1", project_id="p1", baseline_id="b1", occurred_at=now),
        _context("tx"),
    )
    handler(
        ProjectBaselineSubmitted(tenant_id="t1", organization_id="o1", project_id="p1", baseline_id="b1", occurred_at=now),
        _context("tx"),
    )
    assert len(channel.notified) == 1, "same project target within one transaction coalesces"

    handler(
        ProjectBaselineCreated(tenant_id="t1", organization_id="o1", project_id="p2", baseline_id="b2", occurred_at=now),
        _context("tx"),
    )
    assert len(channel.notified) == 2, "a different project within the same transaction is a separate target"

    handler(
        ProjectBaselineCreated(tenant_id="t1", organization_id="o1", project_id="p1", baseline_id="b3", occurred_at=now),
        _context("next-tx"),
    )
    assert len(channel.notified) == 3, "a new transaction is never coalesced with the previous one"


def test_project_a_hint_does_not_match_project_b_exact_resource_filter():
    channel = _fake_channel()
    handler = build_baseline_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        ProjectBaselineApproved(
            tenant_id="t1", organization_id="o1", project_id="project-a", baseline_id="b1",
            superseded_baseline_id=None, occurred_at=now,
        ),
        _context("tx"),
    )
    hint = channel.notified[0]
    project_b_filter = ExactResource(
        tenant_id="t1", organization_id="o1", module_code="project_management",
        entity_type="project", entity_id="project-b",
    )
    project_a_filter = ExactResource(
        tenant_id="t1", organization_id="o1", module_code="project_management",
        entity_type="project", entity_id="project-a",
    )
    assert project_b_filter.matches(hint.scope) is False
    assert project_a_filter.matches(hint.scope) is True


def test_different_organization_hint_is_not_delivered_to_a_scoped_subscription():
    from src.core.shared.events.view_invalidation import ExactOrganization

    channel = _fake_channel()
    handler = build_baseline_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        ProjectBaselineCreated(tenant_id="t1", organization_id="o2", project_id="p1", baseline_id="b1", occurred_at=now),
        _context("tx"),
    )
    hint = channel.notified[0]
    assert ExactOrganization("t1", "o1").matches(hint.scope) is False
    assert ExactOrganization("t1", "o2").matches(hint.scope) is True


# ---------------------------------------------------------------------------
# Real BaselineService producer path (converged onto SqlAlchemyBaselineUnitOfWork)
# ---------------------------------------------------------------------------


def test_create_baseline_produces_exactly_one_project_baseline_hint(services):
    project = _project_with_tasks(services)
    hints = _spy_hints(services)

    baseline_service = services["baseline_service"]
    baseline = baseline_service.create_baseline(project.id, "BL1", rate_as_of=date.today())

    baseline_hints = _baseline_hints(hints)
    assert len(baseline_hints) == 1
    assert baseline_hints[0].scope.entity_id == project.id
    assert baseline.project_id == project.id


def test_submit_baseline_produces_exactly_one_hint(services):
    project = _project_with_tasks(services)
    baseline_service = services["baseline_service"]
    baseline = baseline_service.create_baseline(project.id, "BL1", rate_as_of=date.today())
    hints = _spy_hints(services)

    submitted = baseline_service.submit_baseline(baseline.id, submitted_by="admin")

    baseline_hints = _baseline_hints(hints)
    assert len(baseline_hints) == 1
    assert baseline_hints[0].scope.entity_id == project.id
    assert submitted.status.value == "submitted"


def test_approve_baseline_produces_exactly_one_hint_and_carries_superseded_id(services):
    project = _project_with_tasks(services)
    baseline_service = services["baseline_service"]

    first = baseline_service.create_baseline(project.id, "BL1", rate_as_of=date.today())
    baseline_service.submit_baseline(first.id, submitted_by="admin")
    baseline_service.approve_baseline(first.id, approved_by="admin")

    second = baseline_service.create_baseline(project.id, "BL2", rate_as_of=date.today())
    baseline_service.submit_baseline(second.id, submitted_by="admin")

    # Subscribe directly to the post-commit bus for the typed event itself (not just the
    # ViewInvalidation hint) to prove `superseded_baseline_id` is populated correctly. Reached
    # via the bound `uow_factory` method's own `__self__` -- the post-commit bus itself is not
    # exposed as a top-level services-dict key.
    post_commit_bus = baseline_service._uow_factory.__self__._post_commit_bus
    seen_events: list = []
    post_commit_bus.subscribe(
        ProjectBaselineApproved, lambda event, _context, _seen=seen_events: _seen.append(event)
    )
    hints = _spy_hints(services)

    baseline_service.approve_baseline(second.id, approved_by="admin")

    baseline_hints = _baseline_hints(hints)
    assert len(baseline_hints) == 1
    assert baseline_hints[0].scope.entity_id == project.id
    assert len(seen_events) == 1
    assert seen_events[0].baseline_id == second.id
    assert seen_events[0].superseded_baseline_id == first.id


def test_reject_baseline_produces_exactly_one_hint(services):
    project = _project_with_tasks(services)
    baseline_service = services["baseline_service"]
    baseline = baseline_service.create_baseline(project.id, "BL1", rate_as_of=date.today())
    baseline_service.submit_baseline(baseline.id, submitted_by="admin")
    hints = _spy_hints(services)

    rejected = baseline_service.reject_baseline(baseline.id)

    baseline_hints = _baseline_hints(hints)
    assert len(baseline_hints) == 1
    assert rejected.status.value == "rejected"


def test_delete_baseline_produces_exactly_one_hint(services):
    project = _project_with_tasks(services)
    baseline_service = services["baseline_service"]
    baseline = baseline_service.create_baseline(project.id, "BL1", rate_as_of=date.today())
    hints = _spy_hints(services)

    baseline_service.delete_baseline(baseline.id)

    baseline_hints = _baseline_hints(hints)
    assert len(baseline_hints) == 1
    assert baseline_service._baselines.get_baseline(baseline.id) is None


def test_disallowed_transition_raises_and_produces_zero_hints(services):
    """Approving a DRAFT baseline (never submitted) must raise, never commit, and never notify
    -- the `with uow:` block's rollback-on-exception behavior (P23)."""
    project = _project_with_tasks(services)
    baseline_service = services["baseline_service"]
    baseline = baseline_service.create_baseline(project.id, "BL1", rate_as_of=date.today())
    hints = _spy_hints(services)

    with pytest.raises(ValidationError):
        baseline_service.approve_baseline(baseline.id, approved_by="admin")

    assert _baseline_hints(hints) == []
    assert baseline_service._baselines.get_baseline(baseline.id).status.value == "draft"


def test_baseline_service_shared_session_survives_repeated_commits(services):
    """The custom `SqlAlchemyBaselineUnitOfWork` must never close the shared Session -- proven by
    successfully performing multiple independent commits (create, then submit, then approve) on
    the SAME long-lived `baseline_service` instance, with the Session object itself unchanged
    and still usable throughout."""
    project = _project_with_tasks(services)
    baseline_service = services["baseline_service"]
    session_before = baseline_service._session

    baseline = baseline_service.create_baseline(project.id, "BL1", rate_as_of=date.today())
    baseline_service.submit_baseline(baseline.id, submitted_by="admin")
    approved = baseline_service.approve_baseline(baseline.id, approved_by="admin")

    assert approved.status.value == "approved"
    assert baseline_service._session is session_before
    assert session_before.is_active


# ---------------------------------------------------------------------------
# baseline_changed fully retired
# ---------------------------------------------------------------------------


def test_baseline_changed_field_no_longer_exists():
    assert not hasattr(domain_events, "baseline_changed")


def test_baseline_changed_has_zero_production_references():
    """Checks for actual usage (`domain_events.baseline_changed`) or the field declaration, not
    the bare substring -- `control_workspace_controller.py` carries a deliberate retirement
    comment explaining the P23 removal (matching this session's established convention, e.g.
    P18B's `resources_changed` retirement comments), which would otherwise false-positive a
    blanket substring scan."""
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "domain_events.baseline_changed" in source or "baseline_changed:" in source:
            hits.append(normalized)
    assert hits == [], hits
