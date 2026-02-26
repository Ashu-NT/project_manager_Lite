from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import date, timedelta

import pytest

from core.models import CostType, DependencyType


@dataclass(frozen=True)
class PerfConfig:
    tasks: int
    resources: int
    cost_items: int
    assignment_stride: int
    cross_dependency_gap: int
    start_date: date
    seed_sla_seconds: float
    schedule_sla_seconds: float
    baseline_sla_seconds: float
    report_sla_seconds: float
    dashboard_sla_seconds: float
    total_sla_seconds: float


@dataclass(frozen=True)
class SeedResult:
    project_id: str
    task_ids: list[str]
    dependency_count: int
    assignment_count: int
    cost_count: int


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return float(raw)


def _load_config() -> PerfConfig:
    task_count = _env_int("PM_PERF_TASKS", 5000)
    resource_count = _env_int("PM_PERF_RESOURCES", 1200)
    cost_count = _env_int("PM_PERF_COST_ITEMS", task_count)
    assignment_stride = max(1, _env_int("PM_PERF_ASSIGNMENT_STRIDE", 1))
    cross_dependency_gap = max(2, _env_int("PM_PERF_CROSS_DEP_GAP", 29))

    return PerfConfig(
        tasks=task_count,
        resources=resource_count,
        cost_items=cost_count,
        assignment_stride=assignment_stride,
        cross_dependency_gap=cross_dependency_gap,
        start_date=date.fromisoformat(os.getenv("PM_PERF_START_DATE", "2025-01-06")),
        seed_sla_seconds=_env_float("PM_PERF_SLA_SEED_SECONDS", 30.0),
        schedule_sla_seconds=_env_float("PM_PERF_SLA_SCHEDULE_SECONDS", 15.0),
        baseline_sla_seconds=_env_float("PM_PERF_SLA_BASELINE_SECONDS", 20.0),
        report_sla_seconds=_env_float("PM_PERF_SLA_REPORT_SECONDS", 30.0),
        dashboard_sla_seconds=_env_float("PM_PERF_SLA_DASHBOARD_SECONDS", 30.0),
        total_sla_seconds=_env_float("PM_PERF_SLA_TOTAL_SECONDS", 125.0),
    )


def _timed(metrics: dict[str, float], key: str, fn):
    started = time.perf_counter()
    result = fn()
    metrics[key] = time.perf_counter() - started
    return result


def _seed_large_project(services: dict, config: PerfConfig) -> SeedResult:
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    cs = services["cost_service"]

    project_end = config.start_date + timedelta(days=max(365, config.tasks // 2))
    project = ps.create_project(
        f"Large Perf Project ({config.tasks} tasks)",
        "Synthetic large-scale performance workload",
        start_date=config.start_date,
        end_date=project_end,
        currency="USD",
    )
    project_id = project.id

    resources = []
    for idx in range(config.resources):
        resource = rs.create_resource(
            name=f"Perf Resource {idx + 1:04d}",
            role="Developer",
            hourly_rate=95.0 + float(idx % 7) * 5.0,
            currency_code="USD",
        )
        resources.append(resource)

    tasks = []
    for idx in range(config.tasks):
        task = ts.create_task(
            project_id=project_id,
            name=f"Task {idx + 1:05d}",
            start_date=config.start_date if idx == 0 else None,
            duration_days=1 + (idx % 5),
            priority=idx % 100,
        )
        tasks.append(task)

    dependency_count = 0
    for idx in range(1, len(tasks)):
        ts.add_dependency(tasks[idx - 1].id, tasks[idx].id, DependencyType.FINISH_TO_START, lag_days=0)
        dependency_count += 1

    for idx in range(config.cross_dependency_gap, len(tasks), config.cross_dependency_gap):
        predecessor_idx = idx - config.cross_dependency_gap
        ts.add_dependency(
            tasks[predecessor_idx].id,
            tasks[idx].id,
            DependencyType.FINISH_TO_START,
            lag_days=idx % 3,
        )
        dependency_count += 1

    assignment_count = 0
    for idx, task in enumerate(tasks):
        if idx % config.assignment_stride != 0:
            continue
        resource = resources[idx % len(resources)]
        assignment = ts.assign_resource(
            task_id=task.id,
            resource_id=resource.id,
            allocation_percent=50.0 + float(idx % 3) * 10.0,
        )
        ts.set_assignment_hours(assignment.id, 2.0 + float(idx % 5))
        assignment_count += 1

    cost_count = 0
    limit = min(config.cost_items, len(tasks))
    for idx in range(limit):
        task = tasks[idx]
        cs.add_cost_item(
            project_id=project_id,
            task_id=task.id,
            description=f"Cost Item {idx + 1:05d}",
            planned_amount=250.0 + float(idx % 11) * 10.0,
            committed_amount=90.0 + float(idx % 7) * 5.0,
            actual_amount=70.0 + float(idx % 5) * 5.0,
            cost_type=CostType.OVERHEAD if idx % 4 else CostType.LABOR,
            currency_code="USD",
        )
        if idx % 10 == 0:
            ts.update_progress(task.id, percent_complete=float((idx // 10) % 101))
        cost_count += 1

    return SeedResult(
        project_id=project_id,
        task_ids=[t.id for t in tasks],
        dependency_count=dependency_count,
        assignment_count=assignment_count,
        cost_count=cost_count,
    )


def _run_reporting_phase(services: dict, project_id: str, baseline_id: str):
    rp = services["reporting_service"]
    today = date.today()
    return {
        "kpi": rp.get_project_kpis(project_id),
        "gantt": rp.get_gantt_data(project_id),
        "critical_path": rp.get_critical_path(project_id),
        "resource_load": rp.get_resource_load_summary(project_id),
        "cost_totals": rp.get_project_cost_control_totals(project_id, as_of=today),
        "cost_source": rp.get_project_cost_source_breakdown(project_id, as_of=today),
        "evm": rp.get_earned_value(project_id=project_id, baseline_id=baseline_id, as_of=today),
        "evm_series": rp.get_evm_series(project_id=project_id, baseline_id=baseline_id, as_of=today),
    }


def _assert_slas(metrics: dict[str, float], config: PerfConfig) -> None:
    limits = {
        "seed": config.seed_sla_seconds,
        "schedule": config.schedule_sla_seconds,
        "baseline": config.baseline_sla_seconds,
        "report": config.report_sla_seconds,
        "dashboard": config.dashboard_sla_seconds,
        "total": config.total_sla_seconds,
    }
    breaches = []
    for key, limit in limits.items():
        value = metrics.get(key, 0.0)
        if value > limit:
            breaches.append(f"{key}: {value:.2f}s > {limit:.2f}s")

    if breaches:
        metric_text = ", ".join(f"{k}={v:.2f}s" for k, v in sorted(metrics.items()))
        pytest.fail(f"Large-scale performance SLA breach: {'; '.join(breaches)} | metrics: {metric_text}")


def test_large_scale_performance_workflow(services):
    if not _env_flag("PM_RUN_PERF_TESTS", default=False):
        pytest.skip("Set PM_RUN_PERF_TESTS=1 to run large-scale performance tests.")

    config = _load_config()
    assert config.tasks >= 200, "Large-scale performance test expects at least 200 tasks."
    assert config.resources >= 20, "Large-scale performance test expects at least 20 resources."

    sched = services["scheduling_engine"]
    bs = services["baseline_service"]
    ds = services["dashboard_service"]

    metrics: dict[str, float] = {}
    total_started = time.perf_counter()

    seeded = _timed(metrics, "seed", lambda: _seed_large_project(services, config))

    schedule = _timed(
        metrics,
        "schedule",
        lambda: sched.recalculate_project_schedule(seeded.project_id),
    )
    assert len(schedule) == config.tasks

    baseline = _timed(
        metrics,
        "baseline",
        lambda: bs.create_baseline(seeded.project_id, "Perf Baseline"),
    )

    report_data = _timed(
        metrics,
        "report",
        lambda: _run_reporting_phase(services, seeded.project_id, baseline.id),
    )

    dashboard_data = _timed(
        metrics,
        "dashboard",
        lambda: ds.get_dashboard_data(seeded.project_id, baseline_id=baseline.id),
    )

    metrics["total"] = time.perf_counter() - total_started

    assert report_data["kpi"].tasks_total == config.tasks
    assert len(report_data["gantt"]) == config.tasks
    assert len(report_data["critical_path"]) >= 1
    assert seeded.dependency_count >= config.tasks - 1
    assert seeded.assignment_count > 0
    assert seeded.cost_count == min(config.cost_items, config.tasks)

    assert dashboard_data.kpi.tasks_total == config.tasks
    assert len(dashboard_data.resource_load) > 0

    _assert_slas(metrics, config)
