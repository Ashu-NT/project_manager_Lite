"""Shared fake service implementations for timesheet desktop API tests (project/resource/task fakes)."""
from datetime import date, timedelta
from types import SimpleNamespace

from src.core.modules.project_management.domain.enums import (
    CostType,
    ProjectStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment


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


class _FakeEmployeeService:
    def __init__(self) -> None:
        self._employees: list[SimpleNamespace] = []

    def get_employee(self, employee_id: str) -> SimpleNamespace | None:
        return next((e for e in self._employees if e.id == employee_id), None)

    def list_employees(self, *, active_only: bool | None = None) -> list[SimpleNamespace]:
        return list(self._employees)


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

    def list_resources_by_ids(self, resource_ids: list[str]) -> list[SimpleNamespace]:
        return [r for r in self._resources.values() if r.id in set(resource_ids)]


class _FakeTaskService:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._assignments: dict[str, TaskAssignment] = {}
        self._next_id = 1

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return [task for task in self._tasks.values() if task.project_id == project_id]

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

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)


def _test_period_end(period_start: date) -> date:
    if period_start.month == 12:
        return date.fromordinal(date(period_start.year + 1, 1, 1).toordinal() - 1)
    return date.fromordinal(date(period_start.year, period_start.month + 1, 1).toordinal() - 1)


def _derive_end_date(start_date: date | None, duration_days: int | None) -> date | None:
    if start_date is None or duration_days is None:
        return None
    return start_date + timedelta(days=max(duration_days - 1, 0))
