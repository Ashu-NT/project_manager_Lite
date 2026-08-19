"""R4.4B/D/I/J/K -- ResourceLevelingPlanner, the one authoritative
resource-leveling component. Real, DB-backed `services` fixture
throughout (real Task/TaskAssignment/Resource/TaskDependency rows), not
hand-rolled fakes, so this exercises the actual production data shapes
the planner will run against.
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.application.scheduling.leveling.resource_leveling_planner import (
    ResourceLevelingPlanner,
)
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks


def _snapshot(services, project_id):
    ts = services["task_service"]
    tasks = select_leaf_tasks(ts._task_repo.list_by_project(project_id))
    tasks_by_id = {t.id: t for t in tasks}
    assignments = ts._assignment_repo.list_by_tasks([t.id for t in tasks]) if tasks else []
    deps = ts._dependency_repo.list_by_project(project_id)
    return tasks_by_id, assignments, deps


class TestBasicOverloadResolution:
    def test_single_overload_between_two_independent_tasks_is_resolved(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        rs = services["resource_service"]
        calendar = services["work_calendar_engine"]

        project = ps.create_project("Leveling Planner Single Overload", "")
        task_b = ts.create_task(project.id, "Task B", start_date=date(2026, 9, 7), duration_days=3)
        task_c = ts.create_task(project.id, "Task C", start_date=date(2026, 9, 7), duration_days=3)
        resource = rs.create_resource("Overload Dev", "Developer", hourly_rate=100.0)
        ts.assign_resource(task_b.id, resource.id, allocation_percent=70.0)
        ts.assign_resource(task_c.id, resource.id, allocation_percent=60.0)

        tasks_by_id, assignments, deps = _snapshot(services, project.id)
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
        assert proposal.is_feasible is True
        assert len(proposal.moves) >= 1

    def test_no_conflicts_produces_an_empty_feasible_proposal(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        calendar = services["work_calendar_engine"]

        project = ps.create_project("Leveling Planner No Conflicts", "")
        ts.create_task(project.id, "Solo Task", start_date=date(2026, 9, 7), duration_days=2)

        tasks_by_id, assignments, deps = _snapshot(services, project.id)
        planner = ResourceLevelingPlanner(calendar)
        proposal = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={},
        )

        assert proposal.resource_conflicts_before == 0
        assert proposal.moves == ()
        assert proposal.is_feasible is True


class TestPreviewNeverPersists:
    def test_build_proposal_does_not_write_to_the_repository(self, services):
        """K1: preview must not update Task, increment versions, or
        commit -- confirmed by re-reading the task from the repository
        after building a proposal and asserting nothing changed."""
        ps = services["project_service"]
        ts = services["task_service"]
        rs = services["resource_service"]
        calendar = services["work_calendar_engine"]

        project = ps.create_project("Leveling Planner No Persist", "")
        task_b = ts.create_task(project.id, "Task B", start_date=date(2026, 9, 7), duration_days=3)
        task_c = ts.create_task(project.id, "Task C", start_date=date(2026, 9, 7), duration_days=3)
        resource = rs.create_resource("No Persist Dev", "Developer", hourly_rate=100.0)
        ts.assign_resource(task_b.id, resource.id, allocation_percent=70.0)
        ts.assign_resource(task_c.id, resource.id, allocation_percent=60.0)

        before_version = ts.get_task(task_b.id).version
        before_start = ts.get_task(task_b.id).start_date
        before_floor = ts.get_task(task_b.id).resource_leveling_not_before

        tasks_by_id, assignments, deps = _snapshot(services, project.id)
        planner = ResourceLevelingPlanner(calendar)
        proposal = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={resource.id: resource.name},
        )
        assert len(proposal.moves) >= 1  # setup precondition: a move was actually proposed

        after = ts.get_task(task_b.id)
        assert after.version == before_version
        assert after.start_date == before_start
        assert after.resource_leveling_not_before == before_floor


class TestDependencyAwarePropagation:
    def test_leveling_a_predecessor_propagates_to_its_successor_via_canonical_cpm(self, services):
        """R4.4F/F1: leveling establishes a legal placement for the
        capacity-overloaded predecessor; canonical run_cpm (not the
        planner) propagates the shift onto its successor. The planner
        never manually moves the downstream task.

        task_other is pinned (MUST_START_ON) so it is NOT a legal
        leveling candidate -- otherwise the R4.4I1 priority policy
        (prefer moving a non-critical, positive-float task first) would
        legitimately choose it instead of task_a, which is the more
        interesting case for THIS test but not what it's checking."""
        ps = services["project_service"]
        ts = services["task_service"]
        rs = services["resource_service"]
        calendar = services["work_calendar_engine"]

        project = ps.create_project("Leveling Planner Propagation", "")
        task_a = ts.create_task(project.id, "Task A (overloaded)", start_date=date(2026, 9, 7), duration_days=3)
        task_other = ts.create_task(
            project.id, "Task Other", start_date=date(2026, 9, 7), duration_days=3,
            constraint_type="must_start_on", constraint_date=date(2026, 9, 7),
        )
        task_b = ts.create_task(project.id, "Task B (successor)", duration_days=2)
        ts.add_dependency(task_a.id, task_b.id, DependencyType.FINISH_TO_START, lag_days=0)

        resource = rs.create_resource("Propagation Dev", "Developer", hourly_rate=100.0)
        ts.assign_resource(task_a.id, resource.id, allocation_percent=70.0)
        ts.assign_resource(task_other.id, resource.id, allocation_percent=60.0)

        tasks_by_id, assignments, deps = _snapshot(services, project.id)
        planner = ResourceLevelingPlanner(calendar)
        proposal = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={resource.id: resource.name},
        )

        assert proposal.is_feasible is True
        moved_ids = {m.task_id for m in proposal.moves}
        assert task_a.id in moved_ids
        # B was never directly moved by the planner -- it has no
        # capacity conflict of its own -- but its scheduled position
        # changed as a downstream EFFECT of A's move, verifiable via the
        # project's overall finish date shifting.
        assert task_b.id not in moved_ids
        assert proposal.project_finish_after is not None
        # A moved later, and B (the project's terminal task) depends on
        # A via FS -- the project finish must shift out too, as a
        # canonical-CPM propagation effect, not something the planner
        # computed itself for B.
        assert proposal.project_finish_after > proposal.project_finish_before


class TestMovabilityRespectedByPlanner:
    def test_must_start_on_task_is_never_moved_another_candidate_is_used_instead(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        rs = services["resource_service"]
        calendar = services["work_calendar_engine"]

        project = ps.create_project("Leveling Planner MSO Respected", "")
        task_pinned = ts.create_task(
            project.id, "Pinned Task", start_date=date(2026, 9, 7), duration_days=3,
            constraint_type="must_start_on", constraint_date=date(2026, 9, 7),
        )
        task_flexible = ts.create_task(project.id, "Flexible Task", start_date=date(2026, 9, 7), duration_days=3)
        resource = rs.create_resource("MSO Dev", "Developer", hourly_rate=100.0)
        ts.assign_resource(task_pinned.id, resource.id, allocation_percent=70.0)
        ts.assign_resource(task_flexible.id, resource.id, allocation_percent=60.0)

        tasks_by_id, assignments, deps = _snapshot(services, project.id)
        planner = ResourceLevelingPlanner(calendar)
        proposal = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={resource.id: resource.name},
        )

        moved_ids = {m.task_id for m in proposal.moves}
        assert task_pinned.id not in moved_ids
        if proposal.is_feasible:
            assert task_flexible.id in moved_ids


class TestUnresolvedConflictWhenNoLegalMoveExists:
    def test_two_mso_pinned_tasks_sharing_a_resource_report_unresolved(self, services):
        """R4.4G1/I2/T: when every candidate on an overloaded resource is
        an exact pin, the planner must surface an explicit unresolved
        conflict, never silently claim success."""
        ps = services["project_service"]
        ts = services["task_service"]
        rs = services["resource_service"]
        calendar = services["work_calendar_engine"]

        project = ps.create_project("Leveling Planner Unresolved", "")
        task_1 = ts.create_task(
            project.id, "Pinned One", start_date=date(2026, 9, 7), duration_days=3,
            constraint_type="must_start_on", constraint_date=date(2026, 9, 7),
        )
        task_2 = ts.create_task(
            project.id, "Pinned Two", start_date=date(2026, 9, 7), duration_days=3,
            constraint_type="must_start_on", constraint_date=date(2026, 9, 7),
        )
        resource = rs.create_resource("Unresolved Dev", "Developer", hourly_rate=100.0)
        ts.assign_resource(task_1.id, resource.id, allocation_percent=70.0)
        ts.assign_resource(task_2.id, resource.id, allocation_percent=60.0)

        tasks_by_id, assignments, deps = _snapshot(services, project.id)
        planner = ResourceLevelingPlanner(calendar)
        proposal = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={resource.id: resource.name},
        )

        assert proposal.is_feasible is False
        assert len(proposal.unresolved_conflicts) >= 1
        assert proposal.moves == ()


class TestMultiResourceTaskCandidatePlacement:
    def test_candidate_placement_must_be_clear_on_every_assigned_resource_not_just_the_conflicting_one(self, services):
        """R4.4E1: a task with two assigned resources must only be
        accepted at a candidate date where BOTH resources are free.
        task_multi is overloaded with task_x on Resource X; the planner
        must not "resolve" that by shifting task_multi onto a date that
        is clear for Resource X but collides with task_y on Resource Y,
        which task_multi is also assigned to."""
        ps = services["project_service"]
        ts = services["task_service"]
        rs = services["resource_service"]
        calendar = services["work_calendar_engine"]

        project = ps.create_project("Leveling Planner Multi-Resource", "")
        task_x = ts.create_task(project.id, "Task X", start_date=date(2026, 9, 7), duration_days=3)
        task_multi = ts.create_task(project.id, "Task Multi", start_date=date(2026, 9, 7), duration_days=3)
        task_y = ts.create_task(project.id, "Task Y", start_date=date(2026, 9, 14), duration_days=3)

        resource_x = rs.create_resource("Resource X", "Developer", hourly_rate=100.0)
        resource_y = rs.create_resource("Resource Y", "Developer", hourly_rate=100.0)
        ts.assign_resource(task_x.id, resource_x.id, allocation_percent=70.0)
        ts.assign_resource(task_multi.id, resource_x.id, allocation_percent=60.0)
        ts.assign_resource(task_multi.id, resource_y.id, allocation_percent=60.0)
        ts.assign_resource(task_y.id, resource_y.id, allocation_percent=70.0)

        tasks_by_id, assignments, deps = _snapshot(services, project.id)
        planner = ResourceLevelingPlanner(calendar)
        proposal = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={resource_x.id: resource_x.name, resource_y.id: resource_y.name},
        )

        assert proposal.resource_conflicts_after == 0, (
            "the planner must not report success while a conflict remains on "
            "Resource Y just because it only re-checked Resource X"
        )
        moves_by_task = {m.task_id: m for m in proposal.moves}
        if task_multi.id in moves_by_task:
            move = moves_by_task[task_multi.id]
            assert not (move.new_start <= date(2026, 9, 16) and move.new_finish >= date(2026, 9, 14)), (
                "task_multi must not land on a date that still conflicts with "
                "task_y on Resource Y just because Resource X is clear there"
            )
