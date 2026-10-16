
from datetime import date
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_lifecycle import (
    TaskCreateCommand,
    TaskUpdateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_progress import (
    TaskProgressCommand,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.tests.project_management.api._fake_task_service import _FakeTaskService
from src.tests.project_management.api._project_resource_fakes import (
    _FakeProjectService,
)


def test_task_workspace_page_checks_module_before_query_handler() -> None:
    catalog = SimpleNamespace(
        get_entitlement=lambda _code: SimpleNamespace(
            runtime_enabled=False,
            label="Project Management",
            lifecycle_status="inactive",
        )
    )
    query = SimpleNamespace(
        query_workspace_page=lambda **_kwargs: pytest.fail("query handler called")
    )
    api = build_project_management_tasks_desktop_api(
        task_workspace_query=query,
        module_catalog_service=catalog,
    )

    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        api.list_task_page()


def test_project_management_tasks_desktop_api_lists_statuses() -> None:
    api = build_project_management_tasks_desktop_api()

    statuses = api.list_statuses()

    assert [status.value for status in statuses] == [
        "TODO",
        "IN_PROGRESS",
        "BLOCKED",
        "DONE",
    ]
    assert statuses[1].label == "In Progress"


def test_project_management_tasks_desktop_api_mutates_task_records() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(ProjectCreateCommand(name="Plant Upgrade", description="Replace switchgear and commission the new line."))
    task_service = _FakeTaskService()
    api = build_project_management_tasks_desktop_api(
        project_service=project_service,
        task_lookup_query=task_service, task_hierarchy_query=task_service, task_deletion_commands=task_service, task_progress_commands=task_service, task_hierarchy_commands=task_service, task_constraint_commands=task_service, task_lifecycle_commands=task_service, task_dependency_commands=task_service, task_dependency_query=task_service, task_detail_query=task_service, task_assignment_commands=task_service,
    )

    created = api.create_task(
        TaskCreateCommand(
            project_id=project.id,
            name="Cable Pull",
            description="Primary feeder cable installation.",
            start_date=date(2026, 5, 3),
            duration_days=4,
            status="IN_PROGRESS",
            priority=80,
            deadline=date(2026, 5, 8),
        )
    )

    listed = api.list_tasks(project.id)

    assert created.project_name == "Plant Upgrade"
    assert created.status == "IN_PROGRESS"
    assert created.status_label == "In Progress"
    assert listed[0].name == "Cable Pull"
    assert listed[0].end_date == date(2026, 5, 6)

    updated = api.update_task(
        TaskUpdateCommand(
            task_id=created.id,
            expected_version=task_service.get_task(created.id).version,
            name="Cable Pull Rev A",
            description="Updated execution scope.",
            start_date=date(2026, 5, 4),
            duration_days=5,
            status="BLOCKED",
            priority=95,
            deadline=date(2026, 5, 10),
        )
    )

    assert updated.name == "Cable Pull Rev A"
    assert updated.status == "BLOCKED"
    assert updated.deadline == date(2026, 5, 10)

    progressed = api.update_progress(
        TaskProgressCommand(
            task_id=created.id,
            expected_version=task_service.get_task(created.id).version,
            percent_complete=65.0,
            actual_start=date(2026, 5, 4),
            actual_end=None,
            status="IN_PROGRESS",
        )
    )

    assert progressed.percent_complete == 65.0
    assert progressed.actual_start == date(2026, 5, 4)
    assert progressed.status == "IN_PROGRESS"

    api.delete_task(created.id)

    assert api.list_tasks(project.id) == ()


def test_project_management_tasks_desktop_api_threads_is_milestone() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(ProjectCreateCommand(name="Plant Upgrade", description="Replace switchgear and commission the new line."))
    task_service = _FakeTaskService()
    api = build_project_management_tasks_desktop_api(
        project_service=project_service,
        task_lookup_query=task_service, task_hierarchy_query=task_service, task_deletion_commands=task_service, task_progress_commands=task_service, task_hierarchy_commands=task_service, task_constraint_commands=task_service, task_lifecycle_commands=task_service, task_dependency_commands=task_service, task_dependency_query=task_service, task_detail_query=task_service, task_assignment_commands=task_service,
    )

    created = api.create_task(
        TaskCreateCommand(
            project_id=project.id,
            name="Handover",
            description="",
            start_date=date(2026, 5, 3),
            duration_days=5,
            status="TODO",
            priority=0,
            deadline=None,
            is_milestone=True,
        )
    )

    assert created.is_milestone is True
    assert task_service.get_task(created.id).duration_days == 0

    updated = api.update_task(
        TaskUpdateCommand(
            task_id=created.id,
            expected_version=task_service.get_task(created.id).version,
            name="Handover",
            description="",
            start_date=date(2026, 5, 3),
            duration_days=None,
            status="TODO",
            priority=0,
            deadline=None,
            is_milestone=False,
        )
    )

    assert updated.is_milestone is False


def test_project_management_tasks_desktop_api_uses_task_scoped_project_query() -> None:
    class _TaskScopedProjectService:
        def __init__(self, projects):
            self._projects = list(projects)

        def list_for_task_workspace(self):
            return list(self._projects)

    project_service = _FakeProjectService()
    project = project_service.create_project(ProjectCreateCommand(name="Plant Upgrade", description="Replace switchgear and commission the new line."))
    project.organization_id = "org-test"
    task_service = _FakeTaskService()
    task = task_service.create_task(TaskCreateCommand(project_id=project.id, name="Cable Pull", description="Primary feeder cable installation.", start_date=date(2026, 5, 3), duration_days=4, priority=80, deadline=date(2026, 5, 8)))
    api = build_project_management_tasks_desktop_api(
        project_service=_TaskScopedProjectService([project]),
        task_lookup_query=task_service, task_hierarchy_query=task_service, task_deletion_commands=task_service, task_progress_commands=task_service, task_hierarchy_commands=task_service, task_constraint_commands=task_service, task_lifecycle_commands=task_service, task_dependency_commands=task_service, task_dependency_query=task_service, task_detail_query=task_service, task_assignment_commands=task_service,
    )

    assert [option.label for option in api.list_projects()] == ["Plant Upgrade"]
    assert [row.id for row in api.list_tasks(project.id)] == [task.id]
    assert api.get_task(task.id).project_name == "Plant Upgrade"
