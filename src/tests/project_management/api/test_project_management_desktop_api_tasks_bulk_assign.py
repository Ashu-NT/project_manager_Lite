from datetime import date
from decimal import Decimal

from src.core.modules.project_management.api.desktop import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_assignments import (
    TaskAssignmentAllocationCommand,
    TaskAssignmentCreateCommand,
    TaskAssignmentHoursCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_dependencies import (
    TaskDependencyCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_lifecycle import (
    TaskCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_progress import (
    TaskBulkStatusCommand,
)
from src.core.modules.project_management.domain.enums import (
    TaskStatus,
)
from src.tests.project_management.api._fake_task_service import _FakeTaskService
from src.tests.project_management.api._project_resource_fakes import (
    _FakeProjectResourceQueryHandler,
    _FakeProjectService,
    _FakeResourceService,
)


def test_project_management_tasks_desktop_api_supports_bulk_status_and_delete() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    task_service = _FakeTaskService()
    task_a = task_service.create_task(TaskCreateCommand(project_id=project.id, name="Cable Pull", description="Primary feeder cable installation.", start_date=date(2026, 5, 3), duration_days=4, priority=80, deadline=date(2026, 5, 8)))
    task_b = task_service.create_task(TaskCreateCommand(project_id=project.id, name="Punchlist Closeout", description="Commissioning closeout walkdown.", start_date=date(2026, 5, 8), duration_days=2, priority=60, deadline=date(2026, 5, 10)))
    task_service.set_tasks_status(TaskBulkStatusCommand((task_b.id,), TaskStatus.DONE))
    api = build_project_management_tasks_desktop_api(
        project_service=project_service,
        task_lookup_query=task_service, task_hierarchy_query=task_service, task_deletion_commands=task_service, task_progress_commands=task_service, task_hierarchy_commands=task_service, task_constraint_commands=task_service, task_lifecycle_commands=task_service, task_dependency_commands=task_service, task_dependency_query=task_service, task_detail_query=task_service, task_assignment_commands=task_service,
    )

    changed = api.apply_bulk_status(
        TaskBulkStatusCommand(
            task_ids=(task_a.id, task_b.id, task_a.id, "missing"),
            status="IN_PROGRESS",
            reopen_percent_complete=50.0,
        )
    )

    assert {task.id for task in changed} == {task_a.id, task_b.id}
    assert task_service.get_task(task_a.id).status == TaskStatus.IN_PROGRESS
    assert task_service.get_task(task_b.id).status == TaskStatus.IN_PROGRESS
    assert task_service.get_task(task_b.id).percent_complete == 50.0

    deleted_ids = api.delete_tasks((task_a.id, task_b.id, task_b.id, "missing"))

    assert deleted_ids == (task_a.id, task_b.id)
    assert api.list_tasks(project.id) == ()


def test_project_management_tasks_desktop_api_supports_assignments_and_dependencies() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    resource_service = _FakeResourceService()
    project_resource_query = _FakeProjectResourceQueryHandler()
    task_service = _FakeTaskService()
    task_a = task_service.create_task(TaskCreateCommand(project_id=project.id, name="Cable Pull", description="Primary feeder cable installation.", start_date=date(2026, 5, 3), duration_days=4, priority=80, deadline=date(2026, 5, 8)))
    task_b = task_service.create_task(TaskCreateCommand(project_id=project.id, name="Punchlist Closeout", description="Commissioning closeout walkdown.", start_date=date(2026, 5, 8), duration_days=2, priority=60, deadline=date(2026, 5, 10)))
    resource = resource_service.create_resource(
        name="Alex Taylor",
        role="Planner",
        hourly_rate=85.0,
        currency_code="EUR",
    )
    project_resource = project_resource_query.create(
        project_id=project.id,
        resource_id=resource.id,
        hourly_rate=90.0,
        currency_code="EUR",
    )
    task_service.register_project_resource(project_resource.id, resource.id)
    api = build_project_management_tasks_desktop_api(
        project_service=project_service,
        task_lookup_query=task_service, task_hierarchy_query=task_service, task_deletion_commands=task_service, task_progress_commands=task_service, task_hierarchy_commands=task_service, task_constraint_commands=task_service, task_lifecycle_commands=task_service, task_dependency_commands=task_service, task_dependency_query=task_service, task_detail_query=task_service,
        task_assignment_commands=task_service,
        project_resource_query=project_resource_query,
        resource_query=resource_service,
    )

    assert api.list_project_resources(project.id)[0].label == "Alex Taylor (90.00 EUR/hr)"
    assert [item.value for item in api.list_dependency_types()] == ["FS", "FF", "SS", "SF"]

    assignment = api.create_assignment(
        TaskAssignmentCreateCommand(
            task_id=task_a.id,
            project_resource_id=project_resource.id,
            allocation_percent=55.0,
        )
    )

    assert assignment.resource_name == "Alex Taylor"
    assert assignment.project_resource_id == project_resource.id
    assert api.list_assignments(task_a.id)[0].allocation_percent == 55.0

    updated_assignment = api.update_assignment_allocation(
        TaskAssignmentAllocationCommand(
            assignment_id=assignment.id,
            allocation_percent=72.5,
            expected_version=assignment.version,
        )
    )

    assert updated_assignment.allocation_percent == 72.5

    hours_assignment = api.set_assignment_hours(
        TaskAssignmentHoursCommand(
            assignment_id=assignment.id,
            hours_logged=Decimal(16),
        )
    )

    assert hours_assignment.hours_logged == "16"

    dependency = api.create_dependency(
        TaskDependencyCreateCommand(
            task_id=task_a.id,
            linked_task_id=task_b.id,
            relationship_direction="SUCCESSOR",
            dependency_type="FS",
            lag_days=2,
        )
    )

    assert dependency.direction == "SUCCESSOR"
    assert dependency.linked_task_name == "Punchlist Closeout"
    assert dependency.relationship_label == "Cable Pull -> Punchlist Closeout"
    assert api.list_dependencies(task_a.id)[0].lag_days == 2

    api.delete_dependency(dependency.id)
    api.delete_assignment(assignment.id)

    assert api.list_dependencies(task_a.id) == ()
    assert api.list_assignments(task_a.id) == ()


def test_project_management_tasks_desktop_api_lists_assignments_without_resource_read() -> None:
    class _TaskScopedResourceService:
        def __init__(self, resources):
            self._resources = list(resources)

        def list_for_task_workspace(self, *, resource_ids=()):
            selected = set(resource_ids)
            if not selected:
                return list(self._resources)
            return [resource for resource in self._resources if resource.id in selected]

    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    resource_service = _FakeResourceService()
    project_resource_query = _FakeProjectResourceQueryHandler()
    task_service = _FakeTaskService()
    task = task_service.create_task(TaskCreateCommand(project_id=project.id, name="Cable Pull", description="Primary feeder cable installation.", start_date=date(2026, 5, 3), duration_days=4, priority=80, deadline=date(2026, 5, 8)))
    resource = resource_service.create_resource(
        name="Alex Taylor",
        role="Planner",
        hourly_rate=85.0,
        currency_code="EUR",
    )
    project_resource = project_resource_query.create(
        project_id=project.id,
        resource_id=resource.id,
        hourly_rate=90.0,
        currency_code="EUR",
    )
    task_service.register_project_resource(project_resource.id, resource.id)
    task_service.assign_project_resource(TaskAssignmentCreateCommand(task_id=task.id, project_resource_id=project_resource.id, allocation_percent=55.0))
    api = build_project_management_tasks_desktop_api(
        project_service=project_service,
        task_lookup_query=task_service, task_hierarchy_query=task_service, task_deletion_commands=task_service, task_progress_commands=task_service, task_hierarchy_commands=task_service, task_constraint_commands=task_service, task_lifecycle_commands=task_service, task_dependency_commands=task_service, task_dependency_query=task_service, task_detail_query=task_service, task_assignment_commands=task_service,
        project_resource_query=project_resource_query,
        resource_query=_TaskScopedResourceService([resource]),
    )

    assert api.list_project_resources(project.id)[0].label == "Alex Taylor (90.00 EUR/hr)"
    assert api.list_assignments(task.id)[0].resource_name == "Alex Taylor"
