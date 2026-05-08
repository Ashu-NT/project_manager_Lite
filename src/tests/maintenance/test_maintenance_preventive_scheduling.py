from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta, timezone


def _add_months(anchor: datetime, months: int) -> datetime:
    total_month = anchor.month - 1 + months
    year = anchor.year + total_month // 12
    month = total_month % 12 + 1
    day = min(anchor.day, monthrange(year, month)[1])
    return anchor.replace(year=year, month=month, day=day)


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _build_calendar_plan(
    services,
    *,
    plan_code: str,
    schedule_policy: str,
    generation_lead_value: int = 0,
    generation_lead_unit: str = "days",
) -> tuple[object, object]:
    site = services["site_service"].create_site(site_code=f"{plan_code}-SITE", name=f"{plan_code} Site")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code=f"{plan_code}-AREA",
        name=f"{plan_code} Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code=f"{plan_code}-ASSET",
        name=f"{plan_code} Asset",
    )
    task_template = services["maintenance_task_template_service"].create_task_template(
        task_template_code=f"{plan_code}-TASK",
        name=f"{plan_code} Inspect",
        maintenance_type="preventive",
        template_status="active",
        estimated_minutes=45,
    )
    first_due = datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc)
    plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code=plan_code,
        name=f"{plan_code} Plan",
        asset_id=asset.id,
        status="active",
        plan_type="preventive",
        trigger_mode="calendar",
        schedule_policy=schedule_policy,
        calendar_frequency_unit="monthly",
        calendar_frequency_value=1,
        generation_horizon_count=3,
        generation_lead_value=generation_lead_value,
        generation_lead_unit=generation_lead_unit,
        next_due_at=first_due.isoformat(),
        auto_generate_work_order=True,
    )
    services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="inherit_plan",
    )
    return plan, first_due


def _complete_generated_work_order(services, work_order_id: str) -> object:
    work_order = services["maintenance_work_order_service"].get_work_order(work_order_id)
    planned = services["maintenance_work_order_service"].update_work_order(
        work_order.id,
        status="PLANNED",
        expected_version=work_order.version,
    )
    released = services["maintenance_work_order_service"].update_work_order(
        planned.id,
        status="RELEASED",
        expected_version=planned.version,
    )
    started = services["maintenance_work_order_service"].update_work_order(
        released.id,
        status="IN_PROGRESS",
        expected_version=released.version,
    )
    return services["maintenance_work_order_service"].update_work_order(
        started.id,
        status="COMPLETED",
        expected_version=started.version,
    )


def test_preventive_schedule_refresh_builds_calendar_horizon_instances(services):
    plan, first_due = _build_calendar_plan(services, plan_code="SCH-100", schedule_policy="fixed")

    refreshed = services["maintenance_preventive_generation_service"].refresh_schedule(
        plan_id=plan.id,
        as_of=first_due - timedelta(days=3),
    )
    reloaded_plan = services["maintenance_preventive_plan_service"].find_preventive_plan_by_code("SCH-100")

    due_dates = [row.due_at for row in refreshed if row.plan_id == plan.id and row.status.value == "PLANNED"]

    assert reloaded_plan is not None
    assert reloaded_plan.schedule_policy.value == "FIXED"
    assert reloaded_plan.generation_horizon_count == 3
    assert len(due_dates) == 3
    assert due_dates[0] == first_due
    assert due_dates[1] == datetime(2026, 2, 10, 8, 0, tzinfo=timezone.utc)
    assert due_dates[2] == datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc)


def test_fixed_preventive_schedule_keeps_future_instances_after_completion(services):
    plan, first_due = _build_calendar_plan(services, plan_code="SCH-200", schedule_policy="fixed")
    services["maintenance_preventive_generation_service"].refresh_schedule(plan_id=plan.id, as_of=first_due)

    generation = services["maintenance_preventive_generation_service"].generate_due_work(
        plan_id=plan.id,
        as_of=first_due,
    )[0]
    before_completion = services["maintenance_preventive_generation_service"].list_plan_instances(plan_id=plan.id)
    before_planned_due_dates = [row.due_at for row in before_completion if row.status.value == "PLANNED"]

    _complete_generated_work_order(services, generation.generated_work_order_id)

    after_completion = services["maintenance_preventive_generation_service"].list_plan_instances(plan_id=plan.id)
    after_planned_due_dates = [row.due_at for row in after_completion if row.status.value == "PLANNED"]
    completed_instances = [row for row in after_completion if row.status.value == "COMPLETED"]

    assert generation.generated_work_order_id is not None
    assert before_planned_due_dates == [
        datetime(2026, 2, 10, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc),
    ]
    assert after_planned_due_dates == before_planned_due_dates
    assert len(completed_instances) == 1


def test_floating_preventive_schedule_recalculates_future_instances_from_completion(services):
    plan, first_due = _build_calendar_plan(services, plan_code="SCH-300", schedule_policy="floating")
    services["maintenance_preventive_generation_service"].refresh_schedule(plan_id=plan.id, as_of=first_due)

    generation = services["maintenance_preventive_generation_service"].generate_due_work(
        plan_id=plan.id,
        as_of=first_due,
    )[0]
    before_completion = services["maintenance_preventive_generation_service"].list_plan_instances(plan_id=plan.id)
    before_planned_due_dates = [row.due_at for row in before_completion if row.status.value == "PLANNED"]

    completed = _complete_generated_work_order(services, generation.generated_work_order_id)
    completed_at = completed.actual_end
    services["maintenance_preventive_generation_service"].refresh_schedule(
        plan_id=plan.id,
        as_of=completed_at,
    )

    reloaded_plan = services["maintenance_preventive_plan_service"].find_preventive_plan_by_code("SCH-300")
    after_completion = services["maintenance_preventive_generation_service"].list_plan_instances(plan_id=plan.id)
    after_planned_due_dates = [row.due_at for row in after_completion if row.status.value == "PLANNED"]

    assert generation.generated_work_order_id is not None
    assert before_planned_due_dates == [
        datetime(2026, 2, 10, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc),
    ]
    assert reloaded_plan is not None
    assert _ensure_utc(reloaded_plan.last_completed_at) == completed_at
    expected_due = _add_months(completed_at, 1)
    assert _ensure_utc(reloaded_plan.next_due_at) == expected_due
    assert after_planned_due_dates == [
        expected_due,
        _add_months(expected_due, 1),
        _add_months(expected_due, 2),
    ]


def test_preventive_schedule_enters_due_state_when_generation_lead_window_opens(services):
    plan, first_due = _build_calendar_plan(
        services,
        plan_code="SCH-400",
        schedule_policy="fixed",
        generation_lead_value=5,
        generation_lead_unit="days",
    )

    before_window = services["maintenance_preventive_generation_service"].list_due_candidates(
        plan_id=plan.id,
        as_of=first_due - timedelta(days=6),
    )[0]
    at_window_open = services["maintenance_preventive_generation_service"].list_due_candidates(
        plan_id=plan.id,
        as_of=first_due - timedelta(days=5),
    )[0]

    assert before_window.due_state == "NOT_DUE"
    assert "generation window opens" in before_window.due_reason
    assert at_window_open.due_state == "DUE"
    assert "lead generation window" in at_window_open.due_reason


def test_preventive_generation_can_create_work_order_before_due_date_from_lead_window(services):
    plan, first_due = _build_calendar_plan(
        services,
        plan_code="SCH-500",
        schedule_policy="fixed",
        generation_lead_value=7,
        generation_lead_unit="days",
    )
    generation_as_of = first_due - timedelta(days=4)
    services["maintenance_preventive_generation_service"].refresh_schedule(
        plan_id=plan.id,
        as_of=generation_as_of,
    )

    result = services["maintenance_preventive_generation_service"].generate_due_work(
        plan_id=plan.id,
        as_of=generation_as_of,
    )[0]
    instances = services["maintenance_preventive_generation_service"].list_plan_instances(plan_id=plan.id)
    generated = [row for row in instances if row.generated_work_order_id == result.generated_work_order_id]

    assert result.generated_work_order_id is not None
    assert len(generated) == 1
    assert generated[0].status.value == "GENERATED"
    assert generated[0].due_at == first_due
    assert _ensure_utc(generated[0].generated_at) == generation_as_of


def test_preventive_forecast_preview_exposes_generation_window_and_regeneration_rows(services):
    plan, first_due = _build_calendar_plan(
        services,
        plan_code="SCH-600",
        schedule_policy="fixed",
        generation_lead_value=10,
        generation_lead_unit="days",
    )
    as_of = first_due - timedelta(days=4)

    preview = services["maintenance_preventive_generation_service"].preview_plan_schedule(
        plan_id=plan.id,
        as_of=as_of,
    )

    assert len(preview) == 3
    assert preview[0].due_at == first_due
    assert preview[0].generation_window_opens_at == first_due - timedelta(days=10)
    assert preview[0].planner_state == "READY_WINDOW"
    assert preview[1].planner_state == "UPCOMING"
