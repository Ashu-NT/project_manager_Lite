"""R4.4L -- staleness/concurrency fingerprint for a leveling preview."""
from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment, TaskDependency
from src.core.modules.project_management.application.scheduling.leveling.schedule_fingerprint import (
    compute_schedule_fingerprint,
)
from src.core.modules.project_management.application.scheduling.leveling.resource_leveling_planner import (
    ResourceLevelingPlanner,
)


def _task(task_id: str, **overrides) -> Task:
    base = dict(id=task_id, project_id="p1", name=f"Task {task_id}", duration_days=2, start_date=date(2026, 9, 7))
    base.update(overrides)
    return Task(**base)


def test_fingerprint_is_stable_for_the_same_snapshot_regardless_of_input_order():
    a = _task("a")
    b = _task("b")
    dep = TaskDependency(id="d1", predecessor_task_id="a", successor_task_id="b")
    assignment = TaskAssignment(id="asn1", task_id="a", resource_id="r1")

    fp1 = compute_schedule_fingerprint({"a": a, "b": b}, [dep], [assignment])
    fp2 = compute_schedule_fingerprint({"b": b, "a": a}, [dep], [assignment])

    assert fp1 == fp2


def test_fingerprint_changes_when_a_task_version_changes():
    a = _task("a")
    fp_before = compute_schedule_fingerprint({"a": a}, [], [])

    a_bumped = replace(a, version=a.version + 1)
    fp_after = compute_schedule_fingerprint({"a": a_bumped}, [], [])

    assert fp_before != fp_after


def test_fingerprint_changes_when_a_dependency_version_changes():
    a, b = _task("a"), _task("b")
    dep = TaskDependency(id="d1", predecessor_task_id="a", successor_task_id="b")
    fp_before = compute_schedule_fingerprint({"a": a, "b": b}, [dep], [])

    dep_bumped = replace(dep, version=dep.version + 1)
    fp_after = compute_schedule_fingerprint({"a": a, "b": b}, [dep_bumped], [])

    assert fp_before != fp_after


def test_fingerprint_changes_when_an_assignment_version_changes():
    a = _task("a")
    assignment = TaskAssignment(id="asn1", task_id="a", resource_id="r1")
    fp_before = compute_schedule_fingerprint({"a": a}, [], [assignment])

    assignment_bumped = replace(assignment, version=assignment.version + 1)
    fp_after = compute_schedule_fingerprint({"a": a}, [], [assignment_bumped])

    assert fp_before != fp_after


def test_fingerprint_is_unchanged_when_nothing_relevant_changed():
    a = _task("a")
    fp1 = compute_schedule_fingerprint({"a": a}, [], [])
    fp2 = compute_schedule_fingerprint({"a": _task("a")}, [], [])

    assert fp1 == fp2


class TestPlannerComputesItsOwnFingerprint:
    def test_proposal_fingerprint_matches_independently_recomputed_value_from_the_same_snapshot(self, services):
        """R4.4M's future Apply command must be able to recompute this
        exact token from a freshly re-read database snapshot and compare
        it against the one embedded in the proposal it is applying."""
        ps = services["project_service"]
        ts = services["task_service"]
        rs = services["resource_service"]
        calendar = services["work_calendar_engine"]

        project = ps.create_project("Fingerprint Planner Wiring", "")
        task_b = ts.create_task(project.id, "Task B", start_date=date(2026, 9, 7), duration_days=3)
        task_c = ts.create_task(project.id, "Task C", start_date=date(2026, 9, 7), duration_days=3)
        resource = rs.create_resource("Fingerprint Dev", "Developer", hourly_rate=100.0)
        ts.assign_resource(task_b.id, resource.id, allocation_percent=70.0)
        ts.assign_resource(task_c.id, resource.id, allocation_percent=60.0)

        tasks = ts._task_repo.list_by_project(project.id)
        tasks_by_id = {t.id: t for t in tasks}
        assignments = ts._assignment_repo.list_by_tasks([t.id for t in tasks])
        deps = ts._dependency_repo.list_by_project(project.id)

        planner = ResourceLevelingPlanner(calendar)
        proposal = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={resource.id: resource.name},
        )

        independently_recomputed = compute_schedule_fingerprint(tasks_by_id, deps, assignments)
        assert proposal.schedule_fingerprint == independently_recomputed

    def test_proposal_fingerprint_changes_after_an_unrelated_task_edit_bumps_its_version(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        rs = services["resource_service"]
        calendar = services["work_calendar_engine"]

        project = ps.create_project("Fingerprint Staleness", "")
        task_b = ts.create_task(project.id, "Task B", start_date=date(2026, 9, 7), duration_days=3)
        task_c = ts.create_task(project.id, "Task C", start_date=date(2026, 9, 7), duration_days=3)
        resource = rs.create_resource("Staleness Dev", "Developer", hourly_rate=100.0)
        ts.assign_resource(task_b.id, resource.id, allocation_percent=70.0)
        ts.assign_resource(task_c.id, resource.id, allocation_percent=60.0)

        def _snapshot():
            tasks = ts._task_repo.list_by_project(project.id)
            tasks_by_id = {t.id: t for t in tasks}
            assignments = ts._assignment_repo.list_by_tasks([t.id for t in tasks])
            deps = ts._dependency_repo.list_by_project(project.id)
            return tasks_by_id, assignments, deps

        planner = ResourceLevelingPlanner(calendar)
        tasks_by_id, assignments, deps = _snapshot()
        proposal_1 = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={resource.id: resource.name},
        )

        ts.update_task(task_c.id, name="Task C Renamed")

        tasks_by_id_2, assignments_2, deps_2 = _snapshot()
        proposal_2 = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id_2,
            deps=deps_2,
            assignments=assignments_2,
            resource_name_by_id={resource.id: resource.name},
        )

        assert proposal_1.schedule_fingerprint != proposal_2.schedule_fingerprint
