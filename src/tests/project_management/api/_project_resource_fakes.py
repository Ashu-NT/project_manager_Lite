
from src.core.modules.project_management.application.resources.dto.commands.catalog import (
    ResourceCreateCommand,
    ResourceUpdateCommand,
)

"""Project and resource test doubles for desktop adapter behavior."""

from dataclasses import fields
from types import SimpleNamespace

from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)
from src.core.modules.project_management.application.projects.mappers.project import (
    map_project_response,
)
from src.core.modules.project_management.domain.enums import (
    CostType,
    ProjectStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.projects.project import Project


class _FakeProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._next_id = 1

    def list_projects(self) -> list[Project]:
        return [map_project_response(project) for project in self._projects.values()]

    def list_for_task_workspace(self) -> list[Project]:
        return self.list_projects()

    def create_project(self, command: ProjectCreateCommand) -> Project:
        project = Project(
            id=f"proj-{self._next_id}",
            name=command.name,
            code=command.code,
            description=command.description,
            start_date=command.start_date,
            end_date=command.end_date,
            status=ProjectStatus(command.status),
            client_name=command.client_name,
            client_contact=command.client_contact,
            version=1,
        )
        self._next_id += 1
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Project | None:
        project = self._projects.get(project_id)
        return None if project is None else map_project_response(project)

    def update_project(self, command: ProjectUpdateCommand) -> Project:
        project = self._projects[command.project_id]
        for field in fields(command):
            key = field.name
            if key in {"project_id", "expected_version"}:
                continue
            value = getattr(command, key)
            if key == "status" and value is not None:
                value = ProjectStatus(value)
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

    def list_for_project_workspace(
        self,
        _project_id: str,
        *,
        resource_ids: tuple[str, ...] = (),
    ) -> list[SimpleNamespace]:
        resources = self.list_resources()
        if not resource_ids:
            return resources
        selected = set(resource_ids)
        return [resource for resource in resources if resource.id in selected]

    def list_for_task_workspace(
        self,
        *,
        resource_ids: tuple[str, ...] = (),
    ) -> list[SimpleNamespace]:
        resources = self.list_resources()
        if not resource_ids:
            return resources
        selected = set(resource_ids)
        return [resource for resource in resources if resource.id in selected]

    def create_resource(self, command: ResourceCreateCommand) -> SimpleNamespace:
        employee = self._employee_service.get_employee(command.employee_id) if command.employee_id else None
        resource = SimpleNamespace(
            id=f"res-{self._next_id}",
            name=employee.full_name if employee is not None else command.name,
            role=employee.title if employee is not None else command.role,
            code=command.code or f"RES-{self._next_id:04d}",
            hourly_rate=command.hourly_rate,
            is_active=command.is_active,
            cost_type=CostType(command.cost_type),
            currency_code=(command.currency_code or "").strip().upper() or None,
            version=1,
            capacity_percent=command.capacity_percent,
            address=command.address,
            contact=(employee.email or employee.phone or "") if employee is not None else command.contact,
            worker_type=WorkerType(command.worker_type),
            employee_id=command.employee_id,
        )
        self._next_id += 1
        self._resources[resource.id] = resource
        return resource

    def get_resource(self, resource_id: str) -> SimpleNamespace:
        return self._resources[resource_id]

    def update_resource(self, command: ResourceUpdateCommand) -> SimpleNamespace:
        resource = self._resources[command.resource_id]
        resource.name = command.name
        resource.code = command.code
        resource.kind = command.kind
        resource.role = command.role
        resource.hourly_rate = command.hourly_rate
        resource.cost_type = CostType(command.cost_type)
        resource.currency_code = command.currency_code
        resource.capacity_percent = command.capacity_percent
        resource.address = command.address
        resource.contact = command.contact
        resource.worker_type = WorkerType(command.worker_type)
        resource.employee_id = command.employee_id
        resource.department_id = command.department_id
        resource.site_id = command.site_id
        resource.version += 1
        return resource

    def delete_resource(self, resource_id: str) -> None:
        del self._resources[resource_id]


class _FakeProjectResourceQueryHandler:
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

    def list_for_project_workspace(self, project_id: str) -> list[SimpleNamespace]:
        return self.list_by_project(project_id)

    def list_for_task_workspace(self, project_id: str) -> list[SimpleNamespace]:
        return self.list_by_project(project_id)

    def get(self, project_resource_id: str) -> SimpleNamespace | None:
        return self._project_resources.get(project_resource_id)
