from datetime import date, timedelta
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
from src.core.platform.auth.domain.session import (
    UserSessionContext,
    UserSessionPrincipal,
)
from src.core.platform.common.exceptions import BusinessRuleError


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


def test_project_management_tasks_desktop_api_supports_bulk_status_and_delete() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    task_service = _FakeTaskService()
    task_a = task_service.create_task(
        project_id=project.id,
        name="Cable Pull",
        description="Primary feeder cable installation.",
        start_date=date(2026, 5, 3),
        duration_days=4,
        priority=80,
        deadline=date(2026, 5, 8),
    )
    task_b = task_service.create_task(
        project_id=project.id,
        name="Punchlist Closeout",
        description="Commissioning closeout walkdown.",
        start_date=date(2026, 5, 8),
        duration_days=2,
        priority=60,
        deadline=date(2026, 5, 10),
    )
    task_service.set_status(task_b.id, TaskStatus.DONE)
    api = build_project_management_tasks_desktop_api(
        project_service=project_service,
        task_service=task_service,
    )

    changed = api.apply_bulk_status(
        SimpleNamespace(
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
    project_resource_service = _FakeProjectResourceService()
    task_service = _FakeTaskService()
    task_a = task_service.create_task(
        project_id=project.id,
        name="Cable Pull",
        description="Primary feeder cable installation.",
        start_date=date(2026, 5, 3),
        duration_days=4,
        priority=80,
        deadline=date(2026, 5, 8),
    )
    task_b = task_service.create_task(
        project_id=project.id,
        name="Punchlist Closeout",
        description="Commissioning closeout walkdown.",
        start_date=date(2026, 5, 8),
        duration_days=2,
        priority=60,
        deadline=date(2026, 5, 10),
    )
    resource = resource_service.create_resource(
        name="Alex Taylor",
        role="Planner",
        hourly_rate=85.0,
        currency_code="EUR",
    )
    project_resource = project_resource_service.create(
        project_id=project.id,
        resource_id=resource.id,
        hourly_rate=90.0,
        currency_code="EUR",
    )
    task_service.register_project_resource(project_resource.id, resource.id)
    api = build_project_management_tasks_desktop_api(
        project_service=project_service,
        task_service=task_service,
        project_resource_service=project_resource_service,
        resource_service=resource_service,
    )

    assert api.list_project_resources(project.id)[0].label == "Alex Taylor (90.00 EUR/hr)"
    assert [item.value for item in api.list_dependency_types()] == ["FS", "FF", "SS", "SF"]

    assignment = api.create_assignment(
        SimpleNamespace(
            task_id=task_a.id,
            project_resource_id=project_resource.id,
            allocation_percent=55.0,
        )
    )

    assert assignment.resource_name == "Alex Taylor"
    assert assignment.project_resource_id == project_resource.id
    assert api.list_assignments(task_a.id)[0].allocation_percent == 55.0

    updated_assignment = api.update_assignment_allocation(
        SimpleNamespace(
            assignment_id=assignment.id,
            allocation_percent=72.5,
        )
    )

    assert updated_assignment.allocation_percent == 72.5

    hours_assignment = api.set_assignment_hours(
        SimpleNamespace(
            assignment_id=assignment.id,
            hours_logged=16.0,
        )
    )

    assert hours_assignment.hours_logged == 16.0

    dependency = api.create_dependency(
        SimpleNamespace(
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
    class _ResourceRepo:
        def __init__(self, resources):
            self._resources = {resource.id: resource for resource in resources}

        def list(self):
            return list(self._resources.values())

        def get(self, resource_id):
            return self._resources.get(resource_id)

    class _ResourceReadDeniedService:
        def __init__(self, resources):
            self._resource_repo = _ResourceRepo(resources)
            self._tenant_context_service = SimpleNamespace(
                require_active_organization_id=lambda **_kwargs: "org-test",
            )

        def list_resources(self):
            raise BusinessRuleError(
                "Permission denied for list resources. Missing 'resource.read'."
            )

    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    resource_service = _FakeResourceService()
    project_resource_service = _FakeProjectResourceService()
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
    resource = resource_service.create_resource(
        name="Alex Taylor",
        role="Planner",
        hourly_rate=85.0,
        currency_code="EUR",
    )
    project_resource = project_resource_service.create(
        project_id=project.id,
        resource_id=resource.id,
        hourly_rate=90.0,
        currency_code="EUR",
    )
    task_service.register_project_resource(project_resource.id, resource.id)
    task_service.assign_project_resource(
        task_id=task.id,
        project_resource_id=project_resource.id,
        allocation_percent=55.0,
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
        project_service=project_service,
        task_service=task_service,
        project_resource_service=project_resource_service,
        resource_service=_ResourceReadDeniedService([resource]),
    )

    assert api.list_project_resources(project.id)[0].label == "Alex Taylor (90.00 EUR/hr)"
    assert api.list_assignments(task.id)[0].resource_name == "Alex Taylor"


class _FakeProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._next_id = 1

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def create_project(
        self,
        *,
        name: str,
        description: str = "",
        status: "ProjectStatus | None" = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        planned_budget: float | None = None,
        currency: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Project:
        project = Project(
            id=f"proj-{self._next_id}",
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status=status if status is not None else ProjectStatus.PLANNED,
            client_name=client_name,
            client_contact=client_contact,
            planned_budget=planned_budget,
            currency=(currency or "").strip().upper() or None,
            version=1,
        )
        self._next_id += 1
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def update_project(self, project_id: str, **kwargs) -> Project:
        project = self._projects[project_id]
        for key, value in kwargs.items():
            if value is not None:
                setattr(project, key, value)
        project.version += 1
        return project

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        self._projects[project_id].status = status
        self._projects[project_id].version += 1

    def delete_project(self, project_id: str) -> None:
        del self._projects[project_id]


class _FakeEmployeeService:
    def __init__(self) -> None:
        self._employees = [
            SimpleNamespace(
                id="emp-1",
                employee_code="EMP-001",
                full_name="Alex Taylor",
                title="Planner",
                department="Operations",
                site_name="Plant North",
                email="alex@example.com",
                phone="555-0100",
                is_active=True,
            ),
        ]

    def get_employee(self, employee_id: str) -> SimpleNamespace | None:
        return next((e for e in self._employees if e.id == employee_id), None)

    def list_employees(self, *, active_only: bool | None = None) -> list[SimpleNamespace]:
        if active_only is None:
            return list(self._employees)
        return [e for e in self._employees if bool(e.is_active) == bool(active_only)]


class _FakeResourceService:
    def __init__(self) -> None:
        self._resources: dict[str, SimpleNamespace] = {}
        self._next_id = 1
        self._employee_service = _FakeEmployeeService()

    def list_resources(self) -> list[SimpleNamespace]:
        return list(self._resources.values())

    def create_resource(
        self,
        *,
        name: str,
        role: str = "",
        hourly_rate: float = 0.0,
        is_active: bool = True,
        cost_type: CostType = CostType.LABOR,
        currency_code: str | None = None,
        capacity_percent: float = 100.0,
        address: str = "",
        contact: str = "",
        worker_type: WorkerType = WorkerType.EXTERNAL,
        employee_id: str | None = None,
        code: str = "",
    ) -> SimpleNamespace:
        employee = self._employee_service.get_employee(employee_id) if employee_id else None
        resource = SimpleNamespace(
            id=f"res-{self._next_id}",
            name=employee.full_name if employee is not None else name,
            role=employee.title if employee is not None else role,
            code=code or f"RES-{self._next_id:04d}",
            hourly_rate=hourly_rate,
            is_active=is_active,
            cost_type=cost_type,
            currency_code=(currency_code or "").strip().upper() or None,
            version=1,
            capacity_percent=capacity_percent,
            address=address,
            contact=(employee.email or employee.phone or "") if employee is not None else contact,
            worker_type=worker_type,
            employee_id=employee_id,
        )
        self._next_id += 1
        self._resources[resource.id] = resource
        return resource

    def get_resource(self, resource_id: str) -> SimpleNamespace:
        return self._resources[resource_id]

    def update_resource(self, resource_id: str, **kwargs) -> SimpleNamespace:
        resource = self._resources[resource_id]
        for key, value in kwargs.items():
            if value is not None:
                setattr(resource, key, value)
        resource.version += 1
        return resource

    def delete_resource(self, resource_id: str) -> None:
        del self._resources[resource_id]


class _FakeProjectResourceService:
    def __init__(self) -> None:
        self._project_resources: dict[str, SimpleNamespace] = {}
        self._next_id = 1

    def create(
        self,
        *,
        project_id: str,
        resource_id: str,
        hourly_rate: float | None = None,
        currency_code: str | None = None,
        planned_hours: float = 0.0,
        is_active: bool = True,
    ) -> SimpleNamespace:
        project_resource = SimpleNamespace(
            id=f"pr-{self._next_id}",
            project_id=project_id,
            resource_id=resource_id,
            hourly_rate=hourly_rate,
            currency_code=currency_code,
            planned_hours=planned_hours,
            is_active=is_active,
        )
        self._next_id += 1
        self._project_resources[project_resource.id] = project_resource
        return project_resource

    def list_by_project(self, project_id: str) -> list[SimpleNamespace]:
        return [pr for pr in self._project_resources.values() if pr.project_id == project_id]

    def get(self, project_resource_id: str) -> SimpleNamespace | None:
        return self._project_resources.get(project_resource_id)


class _FakeTaskService:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._assignments: dict[str, TaskAssignment] = {}
        self._dependencies: dict[str, TaskDependency] = {}
        self._project_resource_lookup: dict[str, str] = {}
        self._next_id = 1

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return [task for task in self._tasks.values() if task.project_id == project_id]

    def register_project_resource(self, project_resource_id: str, resource_id: str) -> None:
        self._project_resource_lookup[project_resource_id] = resource_id

    def create_task(
        self,
        *,
        project_id: str,
        name: str,
        code: str = "",
        description: str = "",
        start_date: date | None = None,
        duration_days: int | None = None,
        priority: int = 0,
        deadline: date | None = None,
    ) -> Task:
        task = Task(
            id=f"task-{self._next_id}",
            project_id=project_id,
            name=name,
            code=code,
            description=description,
            start_date=start_date,
            end_date=_derive_end_date(start_date, duration_days),
            duration_days=duration_days,
            priority=priority,
            deadline=deadline,
        )
        self._next_id += 1
        self._tasks[task.id] = task
        return task

    def create_assignment(
        self,
        *,
        task_id: str,
        resource_id: str,
        allocation_percent: float = 100.0,
        hours_logged: float = 0.0,
    ) -> TaskAssignment:
        assignment = TaskAssignment(
            id=f"assign-{len(self._assignments) + 1}",
            task_id=task_id,
            resource_id=resource_id,
            allocation_percent=allocation_percent,
            hours_logged=hours_logged,
        )
        self._assignments[assignment.id] = assignment
        return assignment

    def list_assignments_for_task(self, task_id: str) -> list[TaskAssignment]:
        return [a for a in self._assignments.values() if a.task_id == task_id]

    def list_assignments_for_tasks(self, task_ids: list[str]) -> list[TaskAssignment]:
        task_id_set = {str(tid) for tid in task_ids}
        return [a for a in self._assignments.values() if a.task_id in task_id_set]

    def get_assignment(self, assignment_id: str) -> TaskAssignment | None:
        return self._assignments.get(assignment_id)

    def assign_project_resource(
        self,
        *,
        task_id: str,
        project_resource_id: str,
        allocation_percent: float,
    ) -> TaskAssignment:
        resource_id = self._project_resource_lookup.get(project_resource_id, project_resource_id)
        assignment = self.create_assignment(
            task_id=task_id,
            resource_id=resource_id,
            allocation_percent=allocation_percent,
        )
        assignment.project_resource_id = project_resource_id
        return assignment

    def set_assignment_allocation(self, *, assignment_id: str, allocation_percent: float) -> TaskAssignment:
        assignment = self._assignments[assignment_id]
        assignment.allocation_percent = allocation_percent
        return assignment

    def set_assignment_hours(self, *, assignment_id: str, hours_logged: float) -> TaskAssignment:
        assignment = self._assignments[assignment_id]
        assignment.hours_logged = hours_logged
        return assignment

    def unassign_resource(self, assignment_id: str) -> None:
        del self._assignments[assignment_id]

    def add_dependency(
        self,
        *,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType,
        lag_days: int = 0,
    ) -> TaskDependency:
        dependency = TaskDependency(
            id=f"dep-{len(self._dependencies) + 1}",
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )
        self._dependencies[dependency.id] = dependency
        return dependency

    def list_dependencies_for_task(self, task_id: str) -> list[TaskDependency]:
        return [
            d for d in self._dependencies.values()
            if d.predecessor_task_id == task_id or d.successor_task_id == task_id
        ]

    def remove_dependency(self, dependency_id: str) -> None:
        del self._dependencies[dependency_id]

    def update_task(
        self,
        task_id: str,
        *,
        expected_version: int | None = None,
        name: str | None = None,
        code: str | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
        start_date: date | None = None,
        duration_days: int | None = None,
        priority: int | None = None,
        deadline: date | None = None,
    ) -> Task:
        task = self._tasks[task_id]
        if name is not None:
            task.name = name
        if code is not None and code:
            task.code = code
        if description is not None:
            task.description = description
        if status is not None:
            task.status = status
        if start_date is not None:
            task.start_date = start_date
        if duration_days is not None:
            task.duration_days = duration_days
        if priority is not None:
            task.priority = priority
        if deadline is not None:
            task.deadline = deadline
        task.end_date = _derive_end_date(task.start_date, task.duration_days)
        task.version += 1
        return task

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1

    def update_progress(
        self,
        task_id: str,
        *,
        percent_complete: float | None = None,
        actual_start: date | None = None,
        actual_end: date | None = None,
        status: TaskStatus | None = None,
        expected_version: int | None = None,
    ) -> Task:
        task = self._tasks[task_id]
        if percent_complete is not None:
            task.percent_complete = percent_complete
        if actual_start is not None:
            task.actual_start = actual_start
        if actual_end is not None:
            task.actual_end = actual_end
        if status is not None:
            task.status = status
        task.version += 1
        return task

    def delete_task(self, task_id: str) -> None:
        del self._tasks[task_id]

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)


def _derive_end_date(start_date: date | None, duration_days: int | None) -> date | None:
    if start_date is None or duration_days is None:
        return None
    return start_date + timedelta(days=max(duration_days - 1, 0))
