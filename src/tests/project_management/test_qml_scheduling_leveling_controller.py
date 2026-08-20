"""R4.4Q/R4.4U -- ProjectManagementSchedulingWorkspaceController's new
Resource Leveling surface: previewResourceLeveling()/
applyResourceLeveling() Slots, and the levelingProposal/levelingMoveRows/
levelingMovesTableModel Properties they update. Uses a REAL presenter
backed by the real `services` fixture (not a mock) so the controller's
busy/error/property-update plumbing is exercised against the actual
ResourceLevelingPlanner output, not a faked shape.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.ui_qml.modules.project_management.controllers.scheduling.scheduling_workspace_controller import (
    ProjectManagementSchedulingWorkspaceController,
)
from src.ui_qml.modules.project_management.presenters.scheduling.scheduling_workspace_presenter import (
    ProjectSchedulingWorkspacePresenter,
)


def _controller(qapp, services):
    desktop_api = ProjectManagementSchedulingDesktopApi(
        project_service=services["project_service"],
        task_service=services["task_service"],
        scheduling_engine=services["scheduling_engine"],
        work_calendar_engine=services["work_calendar_engine"],
    )
    scheduling_presenter = ProjectSchedulingWorkspacePresenter(desktop_api=desktop_api)
    return ProjectManagementSchedulingWorkspaceController(
        workspace_presenter=MagicMock(),
        scheduling_workspace_presenter=scheduling_presenter,
    )


def _make_overload(services, name: str):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project(name, "")
    task_b = ts.create_task(project.id, "Task B", start_date=date(2026, 9, 7), duration_days=3)
    task_c = ts.create_task(project.id, "Task C", start_date=date(2026, 9, 7), duration_days=3)
    resource = rs.create_resource("Controller Dev", "Developer", hourly_rate=100.0)
    ts.assign_resource(task_b.id, resource.id, allocation_percent=70.0)
    ts.assign_resource(task_c.id, resource.id, allocation_percent=60.0)
    return project, task_b, task_c


def test_default_leveling_state_prompts_for_a_preview(qapp, services):
    ctrl = _controller(qapp, services)
    assert ctrl.levelingProposal["hasPreview"] is False
    assert ctrl.levelingMoveRows == []
    assert ctrl.levelingMovesTableModel is not None


def test_preview_resource_leveling_populates_the_proposal_and_move_rows(qapp, services):
    ctrl = _controller(qapp, services)
    project, task_b, task_c = _make_overload(services, "Controller Leveling Preview")
    ctrl.selectProject(project.id)

    result = ctrl.previewResourceLeveling()

    assert result["ok"] is True
    assert ctrl.levelingProposal["hasPreview"] is True
    assert len(ctrl.levelingMoveRows) >= 1
    assert ctrl.levelingMovesTableModel.rowCount() == len(ctrl.levelingMoveRows)


def test_apply_resource_leveling_persists_and_resets_the_pending_proposal(qapp, services):
    ts = services["task_service"]
    ctrl = _controller(qapp, services)
    project, task_b, task_c = _make_overload(services, "Controller Leveling Apply")
    ctrl.selectProject(project.id)
    ctrl.previewResourceLeveling()
    moved_task_id = ctrl.levelingMoveRows[0]["taskId"]

    result = ctrl.applyResourceLeveling()

    assert result["ok"] is True
    assert ts.get_task(moved_task_id).resource_leveling_not_before is not None
    # Applied proposal is consumed -- the pending preview state resets so
    # a stale set of moves can never be silently re-applied.
    assert ctrl.levelingProposal["hasPreview"] is False
    assert ctrl.levelingMoveRows == []


def test_apply_without_a_prior_preview_reports_an_error_not_a_crash(qapp, services):
    ctrl = _controller(qapp, services)
    ps = services["project_service"]
    project = ps.create_project("Controller Leveling No Preview", "")
    ctrl.selectProject(project.id)

    result = ctrl.applyResourceLeveling()

    assert result["ok"] is False
    assert ctrl.errorMessage
