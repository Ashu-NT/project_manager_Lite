"""Phase B item 7 (option A) — BaselineService's planned-labor snapshot now
resolves COST rates through the ADR-PF-005 rate-card system instead of
reading Resource.hourly_rate/ProjectResource.hourly_rate directly. This is a
rate-source-consistency fix only: the quantity/allocation model
(ProjectResource.planned_hours, duration-weighted task allocation) is
unchanged, and `BaselineTask.baseline_planned_cost` stays a plain float.

See docs/pm_modernization/project_finance_existing_state_and_implementation_plan.md
Phase B item 7 and test_rate_card_cost_engine_cutover.py (the equivalent
cutover for CostPolicyEngine/LaborCostEngine) for the sibling design this
file mirrors.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError


def _setup_priced_baseline_project(services, *, hourly_rate=50.0, pr_rate=60.0, planned_hours=5.0):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]

    project = ps.create_project("Baseline Rate Cutover", currency="USD")
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource("Engineer", role="DEV", hourly_rate=hourly_rate, currency_code="USD")
    pr = prs.add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        planned_hours=planned_hours,
        hourly_rate=pr_rate,
        currency_code="USD",
    )
    ts.assign_project_resource(task_id=task.id, project_resource_id=pr.id, allocation_percent=100.0)
    return project, task, resource


def test_baseline_uses_rate_card_over_legacy_and_project_override(services) -> None:
    # Resource.hourly_rate=50, ProjectResource.hourly_rate=60, but a
    # project-scoped COST rate-card line says 80 — the baseline must use 80,
    # proving it reads the resolver, not either legacy field.
    services_map = services
    rate_card_service = services["rate_card_service"]
    bs = services["baseline_service"]

    project, task, resource = _setup_priced_baseline_project(
        services_map, hourly_rate=50.0, pr_rate=60.0, planned_hours=5.0
    )
    card = rate_card_service.create_rate_card(name="Project Override", project_id=project.id)
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("80"),
        rate_currency="USD",
        resource_id=resource.id,
    )

    baseline = bs.create_baseline(project.id, "BL", rate_as_of=date.today())
    tasks = bs._baselines.list_tasks(baseline.id)
    assert len(tasks) == 1
    # 5 planned hours x $80 COST rate = $400 — never 50 (legacy) or 60 (PR override).
    assert tasks[0].baseline_planned_cost == pytest.approx(400.0)


def test_baseline_never_uses_billing_rate_type(services) -> None:
    rate_card_service = services["rate_card_service"]
    bs = services["baseline_service"]

    project, task, resource = _setup_priced_baseline_project(
        services, hourly_rate=0.0, pr_rate=None, planned_hours=2.0
    )
    card = rate_card_service.create_rate_card(name="Billing Only", project_id=project.id)
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.BILLING,
        unit="HOUR",
        rate_amount=Decimal("130"),
        rate_currency="USD",
        resource_id=resource.id,
    )
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("80"),
        rate_currency="USD",
        resource_id=resource.id,
    )

    baseline = bs.create_baseline(project.id, "BL", rate_as_of=date.today())
    tasks = bs._baselines.list_tasks(baseline.id)
    # 2 hours x $80 COST rate = $160 — the $130 BILLING line must never
    # influence baseline planned labor.
    assert tasks[0].baseline_planned_cost == pytest.approx(160.0)


def test_missing_rate_fails_baseline_creation_closed(services) -> None:
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    bs = services["baseline_service"]

    project = ps.create_project("Baseline Missing Rate", currency="USD")
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    # hourly_rate=0.0 means create_resource seeds no legacy rate-card line at all.
    resource = rs.create_resource("Unpriced", role="DEV", hourly_rate=0.0)
    pr = prs.add_to_project(project_id=project.id, resource_id=resource.id, planned_hours=3.0)
    ts.assign_project_resource(task_id=task.id, project_resource_id=pr.id, allocation_percent=100.0)

    with pytest.raises(BusinessRuleError) as exc:
        bs.create_baseline(project.id, "BL", rate_as_of=date.today())
    assert exc.value.code == "BASELINE_LABOR_RATE_INCOMPLETE"

    # The whole baseline-creation transaction rolled back — nothing persisted.
    assert bs.list_baselines(project.id) == []


def test_currency_mismatch_fails_baseline_creation_closed(services) -> None:
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    rate_card_service = services["rate_card_service"]
    bs = services["baseline_service"]

    project = ps.create_project("Baseline Currency Mismatch", currency="USD")
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource("Engineer", role="DEV", hourly_rate=0.0)
    pr = prs.add_to_project(project_id=project.id, resource_id=resource.id, planned_hours=4.0)
    ts.assign_project_resource(task_id=task.id, project_resource_id=pr.id, allocation_percent=100.0)

    card = rate_card_service.create_rate_card(name="EUR Card", project_id=project.id)
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("70"),
        rate_currency="EUR",
        resource_id=resource.id,
    )

    with pytest.raises(BusinessRuleError) as exc:
        bs.create_baseline(project.id, "BL", rate_as_of=date.today())
    assert exc.value.code == "BASELINE_LABOR_RATE_CURRENCY_MISMATCH"
    assert bs.list_baselines(project.id) == []


def test_explicit_rate_as_of_selects_correct_historical_rate(services) -> None:
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    rate_card_service = services["rate_card_service"]
    bs = services["baseline_service"]

    project = ps.create_project("Baseline Historical Rate", currency="USD")
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource("Engineer", role="DEV", hourly_rate=0.0)
    pr = prs.add_to_project(project_id=project.id, resource_id=resource.id, planned_hours=1.0)
    ts.assign_project_resource(task_id=task.id, project_resource_id=pr.id, allocation_percent=100.0)

    card = rate_card_service.create_rate_card(name="Revisions", project_id=project.id)
    old_start = date.today() - timedelta(days=60)
    old_end = date.today() - timedelta(days=31)
    new_start = date.today() - timedelta(days=30)
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("50"),
        rate_currency="USD",
        resource_id=resource.id,
        effective_from=old_start,
        effective_to=old_end,
    )
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("90"),
        rate_currency="USD",
        resource_id=resource.id,
        effective_from=new_start,
    )

    old_baseline = bs.create_baseline(
        project.id, "BL-Old", rate_as_of=old_start + timedelta(days=5)
    )
    new_baseline = bs.create_baseline(
        project.id, "BL-New", rate_as_of=new_start + timedelta(days=5)
    )

    old_tasks = bs._baselines.list_tasks(old_baseline.id)
    new_tasks = bs._baselines.list_tasks(new_baseline.id)
    assert old_tasks[0].baseline_planned_cost == pytest.approx(50.0)
    assert new_tasks[0].baseline_planned_cost == pytest.approx(90.0)


def test_later_rate_card_change_does_not_mutate_persisted_baseline(services) -> None:
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    rate_card_service = services["rate_card_service"]
    bs = services["baseline_service"]

    project = ps.create_project("Baseline Frozen Snapshot", currency="USD")
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource("Engineer", role="DEV", hourly_rate=0.0)
    pr = prs.add_to_project(project_id=project.id, resource_id=resource.id, planned_hours=2.0)
    ts.assign_project_resource(task_id=task.id, project_resource_id=pr.id, allocation_percent=100.0)

    card = rate_card_service.create_rate_card(name="Rates", project_id=project.id)
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("80"),
        rate_currency="USD",
        resource_id=resource.id,
        effective_to=date.today(),
    )

    baseline = bs.create_baseline(project.id, "BL", rate_as_of=date.today())
    tasks_before = bs._baselines.list_tasks(baseline.id)
    assert tasks_before[0].baseline_planned_cost == pytest.approx(160.0)  # 2h x $80

    # A later rate-card change (a new, non-overlapping line effective from
    # tomorrow) must not retroactively change the already-persisted
    # baseline snapshot, which is a static float column, not a live view.
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("999"),
        rate_currency="USD",
        resource_id=resource.id,
        effective_from=date.today() + timedelta(days=1),
    )

    tasks_after = bs._baselines.list_tasks(baseline.id)
    assert tasks_after[0].baseline_planned_cost == pytest.approx(160.0)


def test_resolver_is_called_once_via_batch_path(services) -> None:
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    bs = services["baseline_service"]

    project = ps.create_project("Baseline Batch Resolution", currency="USD")
    task_a = ts.create_task(project.id, "Task A", start_date=date.today(), duration_days=2)
    task_b = ts.create_task(project.id, "Task B", start_date=date.today(), duration_days=2)
    resource_1 = rs.create_resource("Engineer One", role="DEV", hourly_rate=40.0, currency_code="USD")
    resource_2 = rs.create_resource("Engineer Two", role="DEV", hourly_rate=60.0, currency_code="USD")
    pr_1 = prs.add_to_project(project_id=project.id, resource_id=resource_1.id, planned_hours=3.0)
    pr_2 = prs.add_to_project(project_id=project.id, resource_id=resource_2.id, planned_hours=2.0)
    ts.assign_project_resource(task_id=task_a.id, project_resource_id=pr_1.id, allocation_percent=100.0)
    ts.assign_project_resource(task_id=task_b.id, project_resource_id=pr_2.id, allocation_percent=100.0)

    call_count = {"n": 0}
    original_resolve_many = bs._rate_resolver.resolve_many

    def _counting_resolve_many(**kwargs):
        call_count["n"] += 1
        assert len(kwargs["resource_ids"]) == len(set(kwargs["resource_ids"]))
        return original_resolve_many(**kwargs)

    bs._rate_resolver.resolve_many = _counting_resolve_many
    try:
        baseline = bs.create_baseline(project.id, "BL", rate_as_of=date.today())
    finally:
        bs._rate_resolver.resolve_many = original_resolve_many

    assert call_count["n"] == 1
    tasks = {t.task_id: t for t in bs._baselines.list_tasks(baseline.id)}
    # 3h x $40 + 2h x $60 = 240, duration-weighted evenly across the two
    # equal-duration tasks -> 120 each.
    total = sum(t.baseline_planned_cost for t in tasks.values())
    assert total == pytest.approx(240.0)
