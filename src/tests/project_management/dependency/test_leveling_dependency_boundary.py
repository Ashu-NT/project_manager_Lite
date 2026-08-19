"""Phase P -- R4.4 RESOURCE LEVELING BOUNDARY.

Do NOT read this file as leveling-migration work. Per the audit
(docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
section 13, finding 3), auto-leveling's only dependency-aware guard is
"refuse to move any task that has a successor" -- a task with an INCOMING
dependency (i.e. a successor edge pointing at it) is not protected at all,
and any leveling shift applied to it is silently discarded the very next
time the canonical schedule is recalculated, because CPM ignores a task's
own persisted start_date whenever it has a usable incoming dependency.

This test PRESERVES that broken interaction as a pinned regression, per
the explicit Phase P instruction: "Do NOT implement resource leveling
changes here... Preserve a regression test proving the current broken
interaction." If R4.4 ever reconciles leveling with dependency minimum
dates through one schedule model (the invariant this phase documents but
does not implement), this test's final assertion should flip -- as a
deliberate, visible change, not a silent regression.
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.domain.enums import DependencyType


def test_auto_leveling_shift_on_a_dependency_linked_task_is_silently_reverted_by_the_next_cpm_run(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Leveling Dependency Boundary", "")
    task_a = ts.create_task(project.id, "Task A", start_date=date(2024, 1, 1), duration_days=2)
    task_b = ts.create_task(project.id, "Task B", duration_days=2)
    ts.add_dependency(task_a.id, task_b.id, DependencyType.FINISH_TO_START, lag_days=0)
    task_c = ts.create_task(project.id, "Task C", start_date=date(2024, 1, 1), duration_days=8)

    resource = rs.create_resource("Leveling Boundary Dev", "Developer", hourly_rate=100.0)
    ts.assign_resource(task_b.id, resource.id, allocation_percent=70.0)
    ts.assign_resource(task_c.id, resource.id, allocation_percent=60.0)

    # Establish B's dependency-driven date first (the baseline the audit
    # says leveling can never actually escape).
    sched.recalculate_project_schedule(project.id)
    dependency_driven_start = ts.get_task(task_b.id).start_date

    result = sched.auto_level_resources(project.id, max_iterations=10)
    assert result.actions, (
        "Setup precondition: expected auto-leveling to find and shift a "
        "conflicting task. If this fails, the resource/date setup above no "
        "longer reproduces a real conflict -- adjust it, don't delete the "
        "regression."
    )

    leveled_b_start = ts.get_task(task_b.id).start_date
    # Setup precondition: the regression is only meaningful if leveling
    # actually moved B (the dependency-linked task) away from its
    # dependency-driven date in the first place.
    assert leveled_b_start != dependency_driven_start

    # THE BUG: the very next canonical recalculation snaps B straight back
    # to its dependency-driven date, with no error, warning, or any signal
    # that the leveling decision above was discarded. DashboardService's
    # real auto-level/manual-shift entry points call
    # recalculate_project_schedule immediately after leveling for exactly
    # this reason, which means production callers hit this today.
    sched.recalculate_project_schedule(project.id)
    reverted_b_start = ts.get_task(task_b.id).start_date

    assert reverted_b_start == dependency_driven_start
    assert reverted_b_start != leveled_b_start
