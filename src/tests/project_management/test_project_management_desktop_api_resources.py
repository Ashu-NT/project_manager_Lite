from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    ResourceCreateCommand,
    ResourceLifecycleCommand,
    ResourceUpdateCommand,
    build_project_management_projects_desktop_api,
    build_project_management_resources_desktop_api,
)
from src.core.modules.project_management.domain.enums import (
    CostType,
    ProjectStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.projects.project import Project


def test_project_management_resources_desktop_api_mutates_resource_records() -> None:
    resource_service = _FakeResourceService()
    employee_service = _FakeEmployeeService()
    api = build_project_management_resources_desktop_api(
        resource_service=resource_service,
        employee_service=employee_service,
    )

    worker_types = api.list_worker_types()
    categories = api.list_categories()
    employee_options = api.list_employees()

    assert [option.value for option in worker_types] == ["EMPLOYEE", "EXTERNAL"]
    assert categories[0].value == "LABOR"
    assert employee_options[0].context == "Operations | Plant North"

    created = api.create_resource(
        ResourceCreateCommand(
            name="Electrical Crew",
            code="",
            kind="CREW",
            role="Lead Technician",
            hourly_rate=Decimal("95"),
            cost_type="LABOR",
            currency_code="eur",
            capacity_percent=110.0,
            address="Site Office",
            contact="crew@example.com",
            worker_type="EXTERNAL",
            employee_id=None,
            department_id=None,
            site_id=None,
        )
    )

    listed = api.list_resources()

    assert created.worker_type == "EXTERNAL"
    assert listed[0].hourly_rate_label == "EUR 95.00"
    assert listed[0].capacity_label == "110.0%"

    employee_resource = api.create_resource(
        ResourceCreateCommand(
            name="",
            code="",
            kind="PERSON",
            role="",
            hourly_rate=Decimal("80"),
            cost_type="LABOR",
            currency_code="usd",
            capacity_percent=100.0,
            address="",
            contact="",
            worker_type="EMPLOYEE",
            employee_id="emp-1",
            department_id=None,
            site_id=None,
        )
    )

    assert employee_resource.name == "Alex Taylor"
    assert employee_resource.employee_context == "Operations | Plant North"

    updated = api.update_resource(
        ResourceUpdateCommand(
            resource_id=created.id,
            expected_version=resource_service.get_resource(created.id).version,
            name="Electrical Crew A",
            code=created.code,
            kind="CREW",
            role="Field Supervisor",
            hourly_rate=Decimal("105"),
            cost_type="EQUIPMENT",
            currency_code="usd",
            capacity_percent=125.0,
            address="Warehouse Annex",
            contact="supervisor@example.com",
            worker_type="EXTERNAL",
            employee_id=None,
            department_id=None,
            site_id=None,
        )
    )

    assert updated.name == "Electrical Crew A"
    assert updated.cost_type == "EQUIPMENT"
    assert updated.hourly_rate_label == "USD 105.00"

    toggled = api.deactivate_resource(
        ResourceLifecycleCommand(
            resource_id=created.id,
            expected_version=resource_service.get_resource(created.id).version,
        )
    )

    assert toggled.is_active is False
    assert toggled.active_label == "Inactive"

    assert {resource.id for resource in api.list_resources()} == {
        created.id,
        employee_resource.id,
    }


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
                department_id=None,
                site_id=None,
                is_active=True,
            ),
            SimpleNamespace(
                id="emp-2",
                employee_code="EMP-002",
                full_name="Jordan Blake",
                title="Supervisor",
                department="Maintenance",
                site_name="Plant South",
                email="jordan@example.com",
                phone="555-0101",
                department_id=None,
                site_id=None,
                is_active=False,
            ),
        ]

    def list_employees(self, *, active_only: bool | None = None) -> list[SimpleNamespace]:
        if active_only is None:
            return list(self._employees)
        return [
            employee
            for employee in self._employees
            if bool(employee.is_active) == bool(active_only)
        ]

    def get_employee(self, employee_id: str) -> SimpleNamespace | None:
        return next((employee for employee in self._employees if employee.id == employee_id), None)


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
        kind="PERSON",
        cost_type: CostType = CostType.LABOR,
        currency_code: str | None = None,
        capacity_percent: float = 100.0,
        address: str = "",
        contact: str = "",
        worker_type: WorkerType = WorkerType.EXTERNAL,
        employee_id: str | None = None,
        code: str = "",
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> SimpleNamespace:
        employee = self._employee_service.get_employee(employee_id) if employee_id else None
        resource = SimpleNamespace(
            id=f"res-{self._next_id}",
            name=employee.full_name if employee is not None else name,
            role=employee.title if employee is not None else role,
            code=code or f"RES-{self._next_id:04d}",
            hourly_rate=hourly_rate,
            is_active=True,
            kind=kind,
            cost_type=cost_type,
            currency_code=(currency_code or "").strip().upper() or None,
            version=1,
            capacity_percent=capacity_percent,
            address=address,
            contact=(employee.email or employee.phone or "") if employee is not None else contact,
            worker_type=worker_type,
            employee_id=employee_id,
            department_id=department_id,
            site_id=site_id,
        )
        self._next_id += 1
        self._resources[resource.id] = resource
        return resource

    def update_resource(
        self,
        *,
        resource_id: str,
        *,
        expected_version: int,
        name: str,
        code: str,
        kind,
        role: str,
        hourly_rate: float,
        cost_type: CostType,
        currency_code: str | None = None,
        capacity_percent: float = 100.0,
        address: str = "",
        contact: str = "",
        worker_type: WorkerType = WorkerType.EXTERNAL,
        employee_id: str | None = None,
        department_id: str | None = None,
        site_id: str | None = None,
        effective_on=None,
    ) -> SimpleNamespace:
        resource = self._resources[resource_id]
        resource.code = code
        resource.kind = kind
        resource.name = name
        resource.role = role
        resource.hourly_rate = hourly_rate
        resource.cost_type = cost_type
        if currency_code is not None:
            resource.currency_code = (currency_code or "").strip().upper() or None
        resource.capacity_percent = capacity_percent
        resource.address = address
        resource.contact = contact
        resource.worker_type = worker_type
        resource.department_id = department_id
        resource.site_id = site_id
        if employee_id is not None:
            employee = self._employee_service.get_employee(employee_id)
            resource.employee_id = employee_id
            if employee is not None:
                resource.name = employee.full_name
                resource.role = employee.title
                resource.contact = employee.email or employee.phone or ""
        elif worker_type == WorkerType.EXTERNAL:
            resource.employee_id = None
        resource.version += 1
        return resource

    def get_resource(self, resource_id: str) -> SimpleNamespace:
        return self._resources[resource_id]

    def deactivate_resource(self, *, resource_id: str, expected_version: int):
        resource = self._resources[resource_id]
        resource.is_active = False
        resource.version += 1
        return resource

    def reactivate_resource(self, *, resource_id: str, expected_version: int):
        resource = self._resources[resource_id]
        resource.is_active = True
        resource.version += 1
        return resource
