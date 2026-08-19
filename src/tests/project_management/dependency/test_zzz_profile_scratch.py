"""Throwaway profiling harness (R4.4W.1 step 1) -- deleted after use.
Measures run_cpm alone, with the REAL services["work_calendar_engine"],
over N independent tasks with zero dependencies, to confirm whether the
O(N^2)-ish scaling observed with a synthetic fake calendar also holds
against the actual production calendar implementation.
"""
from __future__ import annotations

import sys
import time
from datetime import date, timedelta

from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import run_cpm


def _build(n):
    # Plain timedelta arithmetic -- deliberately bypasses the calendar
    # for setup so ONLY run_cpm's own internal calendar calls are
    # measured below, not calendar cost incurred while building tasks.
    base = date(2026, 1, 5)
    tasks = {}
    for i in range(n):
        start = base + timedelta(days=i)
        tasks[f"t{i}"] = Task(id=f"t{i}", project_id="p", name=f"Task {i}", duration_days=2, start_date=start)
    return tasks


def test_profile_run_cpm_real_calendar(services):
    calendar = services["work_calendar_engine"]
    print(f"\nreal calendar class: {type(calendar)}", flush=True)
    sys.stdout.flush()
    for n in (10, 30, 60, 100):
        tasks = _build(n)
        started = time.perf_counter()
        run_cpm(calendar, tasks, [])
        elapsed = time.perf_counter() - started
        print(f"n={n:6d}  run_cpm elapsed={elapsed:8.4f}s  per_task={elapsed/n*1000:8.4f}ms", flush=True)
        sys.stdout.flush()


def test_profile_leveling_planner_real_calendar_and_db(services):
    """Same representative scenario as test_resource_leveling_planner_performance.py
    (one real conflict, N-2 independent background tasks) but through the
    REAL DB-backed services fixture end to end -- real ORM-persisted
    tasks/assignments and the real GlobalCalendarShim, not a hand-rolled
    fake. This is the number that actually matters for R4.4W.1."""
    from datetime import date as _date

    from src.core.modules.project_management.application.scheduling.leveling.resource_leveling_planner import (
        ResourceLevelingPlanner,
    )
    from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks

    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    calendar = services["work_calendar_engine"]

    for n in (100, 1000, 5000):
        project = ps.create_project(f"Perf Real DB N={n}", "")
        resource = rs.create_resource(f"Shared Dev N={n}", "Developer", hourly_rate=100.0)
        setup_started = time.perf_counter()
        for i in range(n):
            start = _date(2026, 1, 5) if i in (0, 1) else _date(2026, 1, 5) + timedelta(days=i + 5)
            task = ts.create_task(project.id, f"Task {i}", start_date=start, duration_days=2)
            if i in (0, 1):
                ts.assign_resource(task.id, resource.id, allocation_percent=70.0 if i == 0 else 60.0)
        setup_elapsed = time.perf_counter() - setup_started

        tasks = select_leaf_tasks(ts._task_repo.list_by_project(project.id))
        tasks_by_id = {t.id: t for t in tasks}
        assignments = ts._assignment_repo.list_by_tasks(list(tasks_by_id))
        deps = ts._dependency_repo.list_by_project(project.id)

        planner = ResourceLevelingPlanner(calendar)
        started = time.perf_counter()
        proposal = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={resource.id: resource.name},
        )
        elapsed = time.perf_counter() - started
        print(
            f"n={n:6d}  setup={setup_elapsed:8.3f}s  build_proposal={elapsed:8.4f}s  "
            f"moves={len(proposal.moves)}  conflicts_after={proposal.resource_conflicts_after}",
            flush=True,
        )
        sys.stdout.flush()


def test_profile_run_cpm_internal_stages_real_db(services):
    """Breaks down ONE run_cpm call at n=1000 real DB-backed tasks into:
    graph build, forward pass, backward pass, schedule-result build --
    and within the calendar itself, counts/times working_days_between vs
    add_working_days/is_working_day, to pin down exactly which calendar
    call dominates (R4.4W.1 step 1/2)."""
    from src.core.modules.project_management.application.scheduling.cpm import (
        graph as graph_mod,
        passes as passes_mod,
        results as results_mod,
    )
    from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import run_cpm

    ps = services["project_service"]
    ts = services["task_service"]
    calendar = services["work_calendar_engine"]

    n = 1000
    project = ps.create_project("Perf Internal Stages", "")
    for i in range(n):
        start = date(2026, 1, 5) + timedelta(days=i)
        ts.create_task(project.id, f"Task {i}", start_date=start, duration_days=2)
    tasks_by_id = {t.id: t for t in ts._task_repo.list_by_project(project.id)}

    class _Counter:
        def __init__(self, real_fn):
            self.real_fn = real_fn
            self.calls = 0
            self.total = 0.0

        def __call__(self, *a, **kw):
            self.calls += 1
            s = time.perf_counter()
            r = self.real_fn(*a, **kw)
            self.total += time.perf_counter() - s
            return r

    graph_counter = _Counter(graph_mod.build_project_dependency_graph)
    fwd_counter = _Counter(passes_mod.run_forward_pass)
    bwd_counter = _Counter(passes_mod.run_backward_pass)
    result_counter = _Counter(results_mod.build_schedule_result)
    wdb_counter = _Counter(calendar.working_days_between)
    awd_counter = _Counter(calendar.add_working_days)
    iwd_counter = _Counter(calendar.is_working_day)

    from unittest.mock import patch
    from src.core.modules.project_management.application.scheduling.cpm import pure_cpm as pure_cpm_mod

    with patch.object(pure_cpm_mod, "build_project_dependency_graph", graph_counter), \
         patch.object(pure_cpm_mod, "run_forward_pass", fwd_counter), \
         patch.object(pure_cpm_mod, "run_backward_pass", bwd_counter), \
         patch.object(pure_cpm_mod, "build_schedule_result", result_counter), \
         patch.object(calendar, "working_days_between", wdb_counter), \
         patch.object(calendar, "add_working_days", awd_counter), \
         patch.object(calendar, "is_working_day", iwd_counter):
        started = time.perf_counter()
        run_cpm(calendar, tasks_by_id, [])
        total = time.perf_counter() - started

    print(f"\n[n={n}] run_cpm total={total:.3f}s", flush=True)
    for label, c in [
        ("build_project_dependency_graph", graph_counter),
        ("run_forward_pass", fwd_counter),
        ("run_backward_pass", bwd_counter),
        ("build_schedule_result", result_counter),
    ]:
        print(f"  stage {label:32s} calls={c.calls:4d} total={c.total:8.3f}s pct={c.total/total*100:5.1f}%", flush=True)
    print("  -- calendar call breakdown (may double-count across stages) --", flush=True)
    for label, c in [
        ("calendar.working_days_between", wdb_counter),
        ("calendar.add_working_days", awd_counter),
        ("calendar.is_working_day", iwd_counter),
    ]:
        mean = (c.total / c.calls * 1000) if c.calls else 0.0
        print(f"  {label:32s} calls={c.calls:6d} total={c.total:8.3f}s mean={mean:8.3f}ms pct={c.total/total*100:5.1f}%", flush=True)
    sys.stdout.flush()
