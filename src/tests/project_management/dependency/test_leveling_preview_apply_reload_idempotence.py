"""R4.4N -- Preview -> Apply -> reload -> run_cpm idempotence.

Per the R4.4 directive, this is THE critical regression: if it fails,
the R4.4 leveling architecture is not complete. It is not enough for a
resource-capacity resolution to hold immediately after Apply -- it must
survive a completely disconnected reload (fresh objects read back from
the repository, no reuse of the pre-apply Python instances) and then
survive repeated canonical CPM recalculation, both via the pure
function directly and via the LIVE persisting SchedulingEngine, without
drifting or the resolved conflict silently reappearing.
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import run_cpm
from src.core.modules.project_management.application.scheduling.leveling.leveling import (
    build_resource_conflicts,
)
from src.core.modules.project_management.application.scheduling.leveling.resource_leveling_planner import (
    ResourceLevelingPlanner,
)
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks


def _snapshot(ts, project_id):
    tasks = select_leaf_tasks(ts._task_repo.list_by_project(project_id))
    tasks_by_id = {t.id: t for t in tasks}
    assignments = ts._assignment_repo.list_by_tasks([t.id for t in tasks]) if tasks else []
    deps = ts._dependency_repo.list_by_project(project_id)
    return tasks_by_id, assignments, deps


class TestPreviewApplyReloadIdempotence:
    def test_resource_conflict_resolution_survives_reload_and_repeated_cpm_via_the_pure_function(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        rs = services["resource_service"]
        calendar = services["work_calendar_engine"]

        project = ps.create_project("Idempotence Pure CPM", "")
        task_b = ts.create_task(project.id, "Task B", start_date=date(2026, 9, 7), duration_days=3)
        task_c = ts.create_task(project.id, "Task C", start_date=date(2026, 9, 7), duration_days=3)
        resource = rs.create_resource("Idempotence Dev", "Developer", hourly_rate=100.0)
        ts.assign_resource(task_b.id, resource.id, allocation_percent=70.0)
        ts.assign_resource(task_c.id, resource.id, allocation_percent=60.0)

        # -- PREVIEW --
        tasks_by_id, assignments, deps = _snapshot(ts, project.id)
        planner = ResourceLevelingPlanner(calendar)
        proposal = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={resource.id: resource.name},
        )
        assert proposal.resource_conflicts_before > 0
        assert proposal.resource_conflicts_after == 0
        assert len(proposal.moves) >= 1, "setup precondition: preview must have proposed at least one move"

        # -- APPLY --
        ts.apply_resource_leveling_plan(project.id, proposal)

        # -- RELOAD -- deliberately fresh objects, not the pre-apply ones,
        # to rule out any bug that only "works" because of Python object
        # identity/caching rather than genuinely persisted state.
        reloaded_tasks_by_id, reloaded_assignments, reloaded_deps = _snapshot(ts, project.id)
        assert reloaded_tasks_by_id is not tasks_by_id
        for task_id, task in reloaded_tasks_by_id.items():
            assert task is not tasks_by_id[task_id]

        # -- run_cpm REPEATEDLY on the reloaded snapshot -- the conflict
        # must stay resolved every time, not just transiently.
        for iteration in range(3):
            result = run_cpm(calendar, reloaded_tasks_by_id, reloaded_deps)
            computed = {tid: info.task for tid, info in result.schedule.items()}
            conflicts = build_resource_conflicts(
                tasks_by_id=computed,
                assignments=reloaded_assignments,
                calendar=calendar,
                resource_name_by_id={resource.id: resource.name},
                threshold_percent=100.0,
            )
            assert conflicts == [], f"conflict reappeared on run_cpm iteration {iteration}"

    def test_resource_conflict_resolution_survives_reload_and_repeated_recalculation_via_the_live_engine(self, services):
        """Same guarantee, but through the LIVE persisting orchestration
        path (SchedulingEngine.recalculate_project_schedule) rather than
        the pure function -- confirmed separately per R4.4A's finding
        that SchedulingEngine and pure_cpm.run_cpm are two independent
        orchestrations sharing only primitives."""
        ps = services["project_service"]
        ts = services["task_service"]
        rs = services["resource_service"]
        calendar = services["work_calendar_engine"]
        sched = services["scheduling_engine"]

        project = ps.create_project("Idempotence Live Engine", "")
        task_b = ts.create_task(project.id, "Task B", start_date=date(2026, 9, 7), duration_days=3)
        task_c = ts.create_task(project.id, "Task C", start_date=date(2026, 9, 7), duration_days=3)
        resource = rs.create_resource("Idempotence Live Dev", "Developer", hourly_rate=100.0)
        ts.assign_resource(task_b.id, resource.id, allocation_percent=70.0)
        ts.assign_resource(task_c.id, resource.id, allocation_percent=60.0)

        tasks_by_id, assignments, deps = _snapshot(ts, project.id)
        planner = ResourceLevelingPlanner(calendar)
        proposal = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={resource.id: resource.name},
        )
        assert len(proposal.moves) >= 1
        moved_task_id = proposal.moves[0].task_id
        expected_start = proposal.moves[0].new_start

        ts.apply_resource_leveling_plan(project.id, proposal)

        # Repeated, DB-backed recalculation across separate calls -- each
        # one reloads from the repository internally; the moved task's
        # start must be stable across all of them, and the resource
        # conflict must never reappear.
        for iteration in range(3):
            sched.recalculate_project_schedule(project.id)

            reloaded_tasks_by_id, reloaded_assignments, _reloaded_deps = _snapshot(ts, project.id)
            assert reloaded_tasks_by_id[moved_task_id].start_date == expected_start, (
                f"moved task's start drifted on recalculation iteration {iteration}"
            )
            conflicts = build_resource_conflicts(
                tasks_by_id=reloaded_tasks_by_id,
                assignments=reloaded_assignments,
                calendar=calendar,
                resource_name_by_id={resource.id: resource.name},
                threshold_percent=100.0,
            )
            assert conflicts == [], f"conflict reappeared on live-engine recalculation iteration {iteration}"
