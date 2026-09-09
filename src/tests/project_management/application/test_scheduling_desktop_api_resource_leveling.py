"""R4.4Q -- ProjectManagementSchedulingDesktopApi.preview_resource_leveling /
apply_resource_leveling: the desktop-API boundary QML calls into for the
new Resource Leveling tab. Preview builds+caches a LevelingProposal and
returns its display DTO; Apply consumes the cached proposal (never a
QML round-trip of the raw domain moves) and hands off to
TaskService.apply_resource_leveling_plan, the already-tested R4.4M/O
command.
"""
from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)


def _desktop_api(services):
    return ProjectManagementSchedulingDesktopApi(
        task_service=services["task_service"],
        scheduling_engine=services["scheduling_engine"],
        work_calendar_engine=services["work_calendar_engine"],
    )


def _make_overload(services, name: str):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project(name, "")
    task_b = ts.create_task(project.id, "Task B", start_date=date(2026, 9, 7), duration_days=3)
    task_c = ts.create_task(project.id, "Task C", start_date=date(2026, 9, 7), duration_days=3)
    resource = rs.create_resource("Desktop API Dev", "Developer", hourly_rate=100.0)
    ts.assign_resource(task_b.id, resource.id, allocation_percent=70.0)
    ts.assign_resource(task_c.id, resource.id, allocation_percent=60.0)
    return project, task_b, task_c


class TestPreview:
    def test_preview_returns_a_dto_describing_the_proposed_moves(self, services):
        api = _desktop_api(services)
        project, task_b, task_c = _make_overload(services, "Desktop API Leveling Preview")

        dto = api.preview_resource_leveling(project.id)

        assert dto.resource_conflicts_before > 0
        assert dto.resource_conflicts_after == 0
        assert len(dto.moves) >= 1
        move = dto.moves[0]
        assert move.task_id in {task_b.id, task_c.id}
        assert move.new_start  # ISO string, non-empty
        assert move.reason

    def test_preview_of_a_conflict_free_project_returns_no_moves(self, services):
        api = _desktop_api(services)
        ps = services["project_service"]
        ts = services["task_service"]
        project = ps.create_project("Desktop API Leveling No Conflicts", "")
        ts.create_task(project.id, "Solo Task", start_date=date(2026, 9, 7), duration_days=2)

        dto = api.preview_resource_leveling(project.id)

        assert dto.moves == ()
        assert dto.is_feasible is True

    def test_preview_with_blank_project_id_returns_an_empty_dto_not_an_error(self, services):
        api = _desktop_api(services)
        dto = api.preview_resource_leveling("")
        assert dto.moves == ()


class TestApply:
    def test_apply_after_preview_persists_the_move_and_returns_the_refreshed_schedule(self, services):
        api = _desktop_api(services)
        ts = services["task_service"]
        project, task_b, task_c = _make_overload(services, "Desktop API Leveling Apply")

        preview = api.preview_resource_leveling(project.id)
        assert len(preview.moves) >= 1
        moved_task_id = preview.moves[0].task_id
        expected_new_start = preview.moves[0].new_start

        schedule = api.apply_resource_leveling(project.id)

        assert ts.get_task(moved_task_id).resource_leveling_not_before.isoformat() == expected_new_start
        assert any(item.id == moved_task_id for item in schedule)

    def test_apply_without_a_prior_preview_raises(self, services):
        api = _desktop_api(services)
        ps = services["project_service"]
        project = ps.create_project("Desktop API Leveling No Preview", "")

        with pytest.raises(ValueError):
            api.apply_resource_leveling(project.id)

    def test_apply_consumes_the_cached_proposal_so_a_second_apply_without_a_new_preview_raises(self, services):
        api = _desktop_api(services)
        project, task_b, task_c = _make_overload(services, "Desktop API Leveling Single Use")
        preview = api.preview_resource_leveling(project.id)
        assert len(preview.moves) >= 1

        api.apply_resource_leveling(project.id)

        with pytest.raises(ValueError):
            api.apply_resource_leveling(project.id)
