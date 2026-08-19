"""R4.4M -- ApplyResourceLevelingPlanCommand (ResourceLevelingApplyMixin).

Persists a previously-computed LevelingProposal: writes each
ProposedTaskMove's new_start onto Task.resource_leveling_not_before,
re-syncs the canonical schedule, and rejects the whole apply if the
schedule has drifted since the preview was built (R4.4L fingerprint).
"""
from __future__ import annotations

from datetime import date

import pytest

from src.core.platform.common.exceptions import ConcurrencyError
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


def _build_overload_proposal(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    calendar = services["work_calendar_engine"]

    project = ps.create_project("Apply Leveling Plan", "")
    task_b = ts.create_task(project.id, "Task B", start_date=date(2026, 9, 7), duration_days=3)
    task_c = ts.create_task(project.id, "Task C", start_date=date(2026, 9, 7), duration_days=3)
    resource = rs.create_resource("Apply Dev", "Developer", hourly_rate=100.0)
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
    return project, task_b, task_c, proposal


class TestApplyHappyPath:
    def test_apply_writes_the_floor_and_the_move_survives_a_fresh_recalculation(self, services):
        ts = services["task_service"]
        project, task_b, task_c, proposal = _build_overload_proposal(services)
        assert len(proposal.moves) >= 1, "setup precondition: the preview must have proposed a move"

        moved_task_id = proposal.moves[0].task_id
        new_start = proposal.moves[0].new_start

        updated = ts.apply_resource_leveling_plan(project.id, proposal)

        assert any(t.id == moved_task_id for t in updated)
        persisted = ts.get_task(moved_task_id)
        assert persisted.resource_leveling_not_before == new_start
        assert persisted.start_date == new_start

        # The floor must survive a SEPARATE, later recalculation too --
        # this is the exact defect R4.4C's floor mechanism exists to fix.
        services["scheduling_engine"].recalculate_project_schedule(project.id)
        assert ts.get_task(moved_task_id).start_date == new_start

    def test_apply_bumps_the_moved_tasks_version(self, services):
        ts = services["task_service"]
        project, task_b, task_c, proposal = _build_overload_proposal(services)
        moved_task_id = proposal.moves[0].task_id
        before_version = ts.get_task(moved_task_id).version

        ts.apply_resource_leveling_plan(project.id, proposal)

        assert ts.get_task(moved_task_id).version > before_version

    def test_applying_an_empty_proposal_is_a_no_op(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        calendar = services["work_calendar_engine"]

        project = ps.create_project("Apply Leveling No Conflicts", "")
        task = ts.create_task(project.id, "Solo Task", start_date=date(2026, 9, 7), duration_days=2)
        before_version = ts.get_task(task.id).version

        tasks_by_id, assignments, deps = _snapshot(ts, project.id)
        planner = ResourceLevelingPlanner(calendar)
        proposal = planner.build_proposal(
            project_id=project.id,
            tasks_by_id=tasks_by_id,
            deps=deps,
            assignments=assignments,
            resource_name_by_id={},
        )
        assert proposal.moves == ()

        result = ts.apply_resource_leveling_plan(project.id, proposal)

        assert result == []
        assert ts.get_task(task.id).version == before_version


class TestApplyRecordsPerTaskAudit:
    def test_apply_records_a_per_task_activity_entry_explaining_the_move(self, services):
        """R4.4P: matching the entity_type='task' convention every other
        schedule-affecting command uses (constraint updates, dependency
        updates, approved financial schedule changes), so the moved
        task's OWN activity feed explains why it moved -- not just a
        project-level summary a viewer would have to go find separately."""
        ts = services["task_service"]
        activity = services["activity_service"]
        project, task_b, task_c, proposal = _build_overload_proposal(services)
        moved = proposal.moves[0]

        ts.apply_resource_leveling_plan(project.id, proposal)

        entries = activity.list_recent(entity_type="task", entity_id=moved.task_id)
        leveling_entries = [e for e in entries if e.action == "scheduling.leveling.apply"]
        assert len(leveling_entries) == 1
        details = leveling_entries[0].details
        assert details["new_start"] == moved.new_start.isoformat()
        assert details["reason"] == moved.reason
        assert details["schedule_fingerprint"] == proposal.schedule_fingerprint


class TestApplyRejectsStaleness:
    def test_apply_rejects_a_proposal_whose_schedule_has_drifted_since_preview(self, services):
        ts = services["task_service"]
        project, task_b, task_c, proposal = _build_overload_proposal(services)
        assert len(proposal.moves) >= 1

        # Someone else edits an involved task after the preview was built,
        # bumping its version and invalidating the fingerprint.
        ts.update_task(task_c.id, name="Task C Renamed By Someone Else")

        with pytest.raises(ConcurrencyError):
            ts.apply_resource_leveling_plan(project.id, proposal)

        # Rejection must not partially apply -- task_b's floor stays unset.
        assert ts.get_task(task_b.id).resource_leveling_not_before is None

    def test_apply_succeeds_when_the_schedule_is_unchanged_since_preview(self, services):
        ts = services["task_service"]
        project, task_b, task_c, proposal = _build_overload_proposal(services)

        updated = ts.apply_resource_leveling_plan(project.id, proposal)

        assert len(updated) >= 1
