from datetime import date
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.domain.enums import (
    CostType,
    DependencyType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.tasks.task import (
    Task,
    TaskAssignment,
    TaskDependency,
)
from src.core.platform.domain.security.auth.session import (
    UserSessionContext,
    UserSessionPrincipal,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.tests.project_management._fake_project_resource_services import (
    _FakeProjectResourceService,
    _FakeProjectService,
    _FakeResourceService,
)
from src.tests.project_management._fake_task_service import _FakeTaskService


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
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    task_service = _FakeTaskService()
    api = build_project_management_tasks_desktop_api(
        project_service=project_service,
        task_service=task_service,
    )

    created = api.create_task(
        SimpleNamespace(
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
        SimpleNamespace(
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
        SimpleNamespace(
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


def test_project_management_tasks_desktop_api_falls_back_to_task_scope_without_project_read() -> None:
    class _ProjectRepo:
        def __init__(self, projects):
            self._projects = {project.id: project for project in projects}

        def list(self):
            return list(self._projects.values())

        def get(self, project_id):
            return self._projects.get(project_id)

    class _ProjectReadDeniedService:
        def __init__(self, projects):
            self._project_repo = _ProjectRepo(projects)
            self._tenant_context_service = SimpleNamespace(
                require_active_organization_id=lambda **_kwargs: "org-test",
            )

        def list_projects(self):
            raise BusinessRuleError(
                "Permission denied for list projects. Missing 'project.read'."
            )

    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    project.organization_id = "org-test"
    task_service = _FakeTaskService()
    task = task_service.create_task(
        project_id=project.id,
        name="Cable Pull",
        description="Primary feeder cable installation.",
        start_date=date(2026, 5, 3),
        duration_days=4,
        priority=80,
        deadline=date(2026, 5, 8),
    )
    user_session = UserSessionContext()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="user-1",
            username="task-reader",
            display_name="Task Reader",
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"task.read"}),
            scoped_access={"project": {project.id: frozenset({"task.read"})}},
        )
    )
    task_service._user_session = user_session

    api = build_project_management_tasks_desktop_api(
        project_service=_ProjectReadDeniedService([project]),
        task_service=task_service,
    )

    assert [option.label for option in api.list_projects()] == ["Plant Upgrade"]
    assert [row.id for row in api.list_all_tasks()] == [task.id]
    assert api.get_task(task.id).project_name == "Plant Upgrade"
