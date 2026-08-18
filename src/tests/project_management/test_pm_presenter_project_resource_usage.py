"""Task Detail Assignment inspector's Project Resource Context wiring
(docs §44 QML follow-up): ProjectTasksWorkspacePresenter.get_project_resource_usage
reads the same ProjectResourceUsageFact the Projects -> Resources workspace
already renders, via the Projects desktop API -- no new calculation."""

from __future__ import annotations

from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.tasks.tasks_workspace_presenter import (
    ProjectTasksWorkspacePresenter,
)


def _fake_usage_dto():
    return SimpleNamespace(
        project_resource_id="pr-1",
        project_id="project-1",
        resource_id="resource-1",
        planned_hours_label="120.0 h",
        allocated_to_tasks_hours_label="100.0 h",
        unallocated_planned_hours_label="20.0 h",
        actual_hours_label="72.0 h",
        remaining_project_hours_label="48.0 h",
        planned_burn_percent=60.0,
        task_assignment_count=3,
        envelope_status="PARTIALLY_ALLOCATED",
        envelope_status_label="Partially Allocated",
        burn_status="WITHIN_PLAN",
        burn_status_label="Within Plan",
    )


def test_get_project_resource_usage_maps_fact_to_camel_case_dict() -> None:
    projects_api = SimpleNamespace(
        get_project_resource_usage=lambda project_resource_id: _fake_usage_dto()
        if project_resource_id == "pr-1"
        else None
    )
    presenter = ProjectTasksWorkspacePresenter(
        desktop_api=SimpleNamespace(),
        projects_desktop_api=projects_api,
    )

    result = presenter.get_project_resource_usage("pr-1")

    assert result == {
        "projectResourceId": "pr-1",
        "projectId": "project-1",
        "resourceId": "resource-1",
        "plannedHoursLabel": "120.0 h",
        "allocatedToTasksHoursLabel": "100.0 h",
        "unallocatedPlannedHoursLabel": "20.0 h",
        "actualHoursLabel": "72.0 h",
        "remainingProjectHoursLabel": "48.0 h",
        "plannedBurnPercent": 60.0,
        "taskAssignmentCount": 3,
        "envelopeStatus": "PARTIALLY_ALLOCATED",
        "envelopeStatusLabel": "Partially Allocated",
        "burnStatus": "WITHIN_PLAN",
        "burnStatusLabel": "Within Plan",
    }


def test_get_project_resource_usage_returns_none_when_not_found() -> None:
    projects_api = SimpleNamespace(get_project_resource_usage=lambda _id: None)
    presenter = ProjectTasksWorkspacePresenter(
        desktop_api=SimpleNamespace(),
        projects_desktop_api=projects_api,
    )

    assert presenter.get_project_resource_usage("does-not-exist") is None


def test_get_project_resource_usage_returns_none_without_projects_api() -> None:
    presenter = ProjectTasksWorkspacePresenter(
        desktop_api=SimpleNamespace(),
        projects_desktop_api=None,
    )

    assert presenter.get_project_resource_usage("pr-1") is None


def test_get_project_resource_usage_returns_none_for_blank_id() -> None:
    projects_api = SimpleNamespace(get_project_resource_usage=lambda _id: _fake_usage_dto())
    presenter = ProjectTasksWorkspacePresenter(
        desktop_api=SimpleNamespace(),
        projects_desktop_api=projects_api,
    )

    assert presenter.get_project_resource_usage("") is None


def test_get_project_resource_usage_swallows_lookup_exceptions() -> None:
    def _raise(_id):
        raise RuntimeError("boom")

    projects_api = SimpleNamespace(get_project_resource_usage=_raise)
    presenter = ProjectTasksWorkspacePresenter(
        desktop_api=SimpleNamespace(),
        projects_desktop_api=projects_api,
    )

    assert presenter.get_project_resource_usage("pr-1") is None
