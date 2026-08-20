"""R4.4Q -- presenter-layer shaping for the Resource Leveling tab:
build_resource_leveling_state() turns the desktop API's DTO into the
plain camelCase dict QML consumes, and
ProjectSchedulingWorkspacePresenter.preview_resource_leveling/
apply_resource_leveling delegate to it and to the desktop API's apply
call respectively.
"""
from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.ui_qml.modules.project_management.presenters.scheduling.leveling_builder import (
    build_resource_leveling_state,
)
from src.ui_qml.modules.project_management.presenters.scheduling.scheduling_workspace_presenter import (
    ProjectSchedulingWorkspacePresenter,
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
    resource = rs.create_resource("Presenter Dev", "Developer", hourly_rate=100.0)
    ts.assign_resource(task_b.id, resource.id, allocation_percent=70.0)
    ts.assign_resource(task_c.id, resource.id, allocation_percent=60.0)
    return project, task_b, task_c


class TestBuildResourceLevelingState:
    def test_blank_project_id_returns_a_prompt_empty_state(self, services):
        api = _desktop_api(services)
        state = build_resource_leveling_state(api, "")
        assert state["hasPreview"] is False
        assert state["moves"] == []
        assert state["emptyState"]

    def test_conflict_free_project_reports_no_moves_with_an_explanatory_empty_state(self, services):
        api = _desktop_api(services)
        ps = services["project_service"]
        ts = services["task_service"]
        project = ps.create_project("Presenter Leveling No Conflicts", "")
        ts.create_task(project.id, "Solo Task", start_date=date(2026, 9, 7), duration_days=2)

        state = build_resource_leveling_state(api, project.id)

        assert state["hasPreview"] is True
        assert state["moves"] == []
        assert "No resource capacity conflicts" in state["emptyState"]

    def test_overloaded_project_returns_camel_case_move_rows_with_status_labels(self, services):
        api = _desktop_api(services)
        project, task_b, task_c = _make_overload(services, "Presenter Leveling Overload")

        state = build_resource_leveling_state(api, project.id)

        assert state["hasPreview"] is True
        assert state["resourceConflictsBefore"] > 0
        assert state["resourceConflictsAfter"] == 0
        assert len(state["moves"]) >= 1
        row = state["moves"][0]
        assert row["id"] == row["taskId"]
        assert row["taskName"]
        assert row["statusLabel"] in {"Resolved", "Critical", "Infeasible", "Deadline Risk"}
        assert "->" in row["shiftLabel"]

    def test_unresolved_conflict_is_reported_never_silently_dropped(self, services):
        api = _desktop_api(services)
        ps = services["project_service"]
        ts = services["task_service"]
        rs = services["resource_service"]
        project = ps.create_project("Presenter Leveling Unresolved", "")
        task_1 = ts.create_task(
            project.id, "Pinned One", start_date=date(2026, 9, 7), duration_days=3,
            constraint_type="must_start_on", constraint_date=date(2026, 9, 7),
        )
        task_2 = ts.create_task(
            project.id, "Pinned Two", start_date=date(2026, 9, 7), duration_days=3,
            constraint_type="must_start_on", constraint_date=date(2026, 9, 7),
        )
        resource = rs.create_resource("Presenter Unresolved Dev", "Developer", hourly_rate=100.0)
        ts.assign_resource(task_1.id, resource.id, allocation_percent=70.0)
        ts.assign_resource(task_2.id, resource.id, allocation_percent=60.0)

        state = build_resource_leveling_state(api, project.id)

        assert state["isFeasible"] is False
        assert len(state["unresolvedConflicts"]) >= 1
        assert state["unresolvedConflicts"][0]["reason"]


class TestPresenterDelegation:
    def test_preview_resource_leveling_delegates_to_the_builder(self, services):
        presenter = ProjectSchedulingWorkspacePresenter(desktop_api=_desktop_api(services))
        project, task_b, task_c = _make_overload(services, "Presenter Delegation Preview")

        state = presenter.preview_resource_leveling(project.id)

        assert state["hasPreview"] is True
        assert len(state["moves"]) >= 1

    def test_apply_resource_leveling_persists_after_a_preview(self, services):
        ts = services["task_service"]
        api = _desktop_api(services)
        presenter = ProjectSchedulingWorkspacePresenter(desktop_api=api)
        project, task_b, task_c = _make_overload(services, "Presenter Delegation Apply")

        state = presenter.preview_resource_leveling(project.id)
        moved_task_id = state["moves"][0]["taskId"]

        presenter.apply_resource_leveling(project.id)

        assert ts.get_task(moved_task_id).resource_leveling_not_before is not None

    def test_apply_resource_leveling_without_a_prior_preview_raises(self, services):
        presenter = ProjectSchedulingWorkspacePresenter(desktop_api=_desktop_api(services))
        ps = services["project_service"]
        project = ps.create_project("Presenter Delegation No Preview", "")

        with pytest.raises(ValueError):
            presenter.apply_resource_leveling(project.id)
