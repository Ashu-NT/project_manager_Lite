
from decimal import Decimal
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_resources_desktop_api,
)
from src.core.modules.project_management.application.resources.dto.commands.catalog import (
    ResourceCreateCommand,
    ResourceLifecycleCommand,
    ResourceUpdateCommand,
)
from src.core.modules.project_management.domain.enums import (
    CostType,
    WorkerType,
)


def test_project_management_resources_desktop_api_mutates_resource_records() -> None:
    resource_service = _FakeResourceService()
    employee_service = _FakeEmployeeService()
    api = build_project_management_resources_desktop_api(
        resource_query=resource_service, resource_master_commands=resource_service, resource_capability_commands=resource_service,
        employee_query=employee_service,
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
            hourly_rate=Decimal(95),
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
                name="Alex Taylor",
            code="",
            kind="PERSON",
            role="",
            hourly_rate=Decimal(80),
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
            hourly_rate=Decimal(105),
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

    def create_resource(self, command: ResourceCreateCommand) -> SimpleNamespace:
        employee = self._employee_service.get_employee(command.employee_id) if command.employee_id else None
        resource = SimpleNamespace(
            id=f"res-{self._next_id}",
            name=employee.full_name if employee is not None else command.name,
            role=employee.title if employee is not None else command.role,
            code=command.code or f"RES-{self._next_id:04d}",
            hourly_rate=command.hourly_rate,
            is_active=True,
            kind=command.kind,
            cost_type=CostType(command.cost_type),
            currency_code=(command.currency_code or "").strip().upper() or None,
            version=1,
            capacity_percent=command.capacity_percent,
            address=command.address,
            contact=(employee.email or employee.phone or "") if employee is not None else command.contact,
            worker_type=WorkerType(command.worker_type),
            employee_id=command.employee_id,
            department_id=command.department_id,
            site_id=command.site_id,
        )
        self._next_id += 1
        self._resources[resource.id] = resource
        return resource

    def update_resource(self, command: ResourceUpdateCommand) -> SimpleNamespace:
        resource = self._resources[command.resource_id]
        resource.code = command.code
        resource.kind = command.kind
        resource.name = command.name
        resource.role = command.role
        resource.hourly_rate = command.hourly_rate
        resource.cost_type = CostType(command.cost_type)
        if command.currency_code is not None:
            resource.currency_code = (command.currency_code or "").strip().upper() or None
        resource.capacity_percent = command.capacity_percent
        resource.address = command.address
        resource.contact = command.contact
        resource.worker_type = WorkerType(command.worker_type)
        resource.department_id = command.department_id
        resource.site_id = command.site_id
        if command.employee_id is not None:
            employee = self._employee_service.get_employee(command.employee_id)
            resource.employee_id = command.employee_id
            if employee is not None:
                resource.name = employee.full_name
                resource.role = employee.title
                resource.contact = employee.email or employee.phone or ""
        elif WorkerType(command.worker_type) == WorkerType.EXTERNAL:
            resource.employee_id = None
        resource.version += 1
        return resource

    def get_resource(self, resource_id: str) -> SimpleNamespace:
        return self._resources[resource_id]

    def deactivate_resource(self, command: ResourceLifecycleCommand) -> SimpleNamespace:
        resource = self._resources[command.resource_id]
        resource.is_active = False
        resource.version += 1
        return resource

    def reactivate_resource(self, command: ResourceLifecycleCommand) -> SimpleNamespace:
        resource = self._resources[command.resource_id]
        resource.is_active = True
        resource.version += 1
        return resource
