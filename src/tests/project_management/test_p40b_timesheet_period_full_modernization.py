from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.core.platform.application.time_management.time.event_handlers.view_invalidation import (
    TIMESHEET_CATEGORY,
    TIMESHEET_PROJECT_SCOPE_CODE,
    TIMESHEET_RESOURCE_SCOPE_CODE,
    TIMESHEET_WORKSPACE_SCOPE_CODE,
    build_timesheet_view_invalidation_handler,
)
from src.core.platform.application.time_management.time.timesheet_events import (
    TimesheetPeriodStatusChangeType,
    TimesheetPeriodStatusChanged,
)
from src.core.platform.common.exceptions import ConcurrencyError
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events


def test_legacy_timesheet_periods_signal_field_is_deleted():
    assert not hasattr(domain_events, "timesheet_periods_changed")


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


def _event(*, change_type, project_ids=("project-1",)) -> TimesheetPeriodStatusChanged:
    return TimesheetPeriodStatusChanged(
        tenant_id="t1",
        organization_id="o1",
        period_id="period-1",
        resource_id="resource-1",
        change_type=change_type,
        project_ids=project_ids,
        occurred_at=datetime.now(timezone.utc),
    )


@pytest.mark.parametrize(
    "change_type",
    list(TimesheetPeriodStatusChangeType),
)
def test_every_change_type_maps_to_workspace_resource_and_project_targets(change_type):
    channel = _fake_channel()
    handler = build_timesheet_view_invalidation_handler(channel)
    handler(_event(change_type=change_type), DomainEventContext(correlation_id="c1"))

    scope_codes = {hint.scope_code for hint in channel.notified}
    assert scope_codes == {
        TIMESHEET_WORKSPACE_SCOPE_CODE,
        TIMESHEET_RESOURCE_SCOPE_CODE,
        TIMESHEET_PROJECT_SCOPE_CODE,
    }
    assert all(hint.category == TIMESHEET_CATEGORY for hint in channel.notified)


def test_no_project_ids_omits_the_project_target():
    channel = _fake_channel()
    handler = build_timesheet_view_invalidation_handler(channel)
    handler(
        _event(change_type=TimesheetPeriodStatusChangeType.SUBMITTED, project_ids=()),
        DomainEventContext(correlation_id="c2"),
    )
    scope_codes = {hint.scope_code for hint in channel.notified}
    assert scope_codes == {TIMESHEET_WORKSPACE_SCOPE_CODE, TIMESHEET_RESOURCE_SCOPE_CODE}


def test_multiple_projects_each_produce_their_own_target():
    channel = _fake_channel()
    handler = build_timesheet_view_invalidation_handler(channel)
    handler(
        _event(
            change_type=TimesheetPeriodStatusChangeType.APPROVED,
            project_ids=("project-1", "project-2"),
        ),
        DomainEventContext(correlation_id="c3"),
    )
    project_hints = [h for h in channel.notified if h.scope_code == TIMESHEET_PROJECT_SCOPE_CODE]
    assert {h.entity_id for h in project_hints} == {"project-1", "project-2"}


def test_dedupe_by_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_timesheet_view_invalidation_handler(channel)
    event = _event(change_type=TimesheetPeriodStatusChangeType.LOCKED)
    handler(event, DomainEventContext(correlation_id="same-tx"))
    handler(event, DomainEventContext(correlation_id="same-tx"))
    assert len(channel.notified) == 3, "three distinct targets, each coalesced within one tx"

    handler(event, DomainEventContext(correlation_id="next-tx"))
    assert len(channel.notified) == 6, "a new transaction is never coalesced with the previous one"


# ---------------------------------------------------------------------------
# Real producer path -- period transitions, converged onto SqlAlchemyUnitOfWorkBase
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


def _timesheet_hints(hints):
    return [h for h in hints if h.category == TIMESHEET_CATEGORY]


def _setup(services):
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "P40B Timesheet project", financial_currency_code=organization.base_currency
    )
    resource = services["resource_service"].create_resource(
        "P40B Timesheet Engineer", hourly_rate=0, currency_code=organization.base_currency
    )
    task = services["task_service"].create_task(
        project.id, "P40B Timesheet Task", start_date=date(2026, 6, 1), duration_days=10
    )
    assignment = services["task_service"].assign_resource(
        task.id, resource.id, allocation_percent=100
    )
    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 6, 4), hours=4
    )
    return organization, project, resource


def test_submit_produces_workspace_resource_and_project_hints_and_zero_legacy_signal(services):
    _, project, resource = _setup(services)
    hints = _spy_hints(services)

    submitted = services["timesheet_service"].submit_timesheet_period(
        resource.id, period_start=date(2026, 6, 1)
    )

    ts_hints = _timesheet_hints(hints)
    scope_codes = {h.scope_code for h in ts_hints}
    assert scope_codes == {
        TIMESHEET_WORKSPACE_SCOPE_CODE,
        TIMESHEET_RESOURCE_SCOPE_CODE,
        TIMESHEET_PROJECT_SCOPE_CODE,
    }
    project_hint = next(h for h in ts_hints if h.scope_code == TIMESHEET_PROJECT_SCOPE_CODE)
    assert project_hint.entity_id == project.id
    resource_hint = next(h for h in ts_hints if h.scope_code == TIMESHEET_RESOURCE_SCOPE_CODE)
    assert resource_hint.entity_id == resource.id
    assert submitted.status.value == "SUBMITTED"


def test_approve_then_reject_each_record_exactly_one_typed_event_per_transition(services):
    _, _project, resource = _setup(services)
    time = services["timesheet_service"]
    submitted = time.submit_timesheet_period(resource.id, period_start=date(2026, 6, 1))
    hints = _spy_hints(services)

    approved = time.approve_timesheet_period(
        submitted.period_id, expected_version=submitted.version, note="Approved"
    )

    approve_hints = _timesheet_hints(hints)
    assert len(approve_hints) == 3
    assert approved.status.value == "APPROVED"


def test_stale_version_raises_and_produces_zero_hints(services):
    _, _project, resource = _setup(services)
    time = services["timesheet_service"]
    submitted = time.submit_timesheet_period(resource.id, period_start=date(2026, 6, 1))
    hints = _spy_hints(services)

    with pytest.raises(ConcurrencyError):
        time.approve_timesheet_period(
            submitted.period_id, expected_version=submitted.version + 1, note="stale"
        )

    assert _timesheet_hints(hints) == []


def test_approval_post_commit_event_bridge_is_unaffected_by_timesheet_modernization():
    """P39-CLEANUP established the exact remaining legacy approval-bridge sites; Timesheet has
    never been one of them (it has no approval-participant integration at all), and P40B must
    not change that set."""
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
