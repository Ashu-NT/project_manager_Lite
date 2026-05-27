from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.platform.org import EmployeeService


@dataclass(frozen=True)
class ResourceWorkerTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class ResourceCategoryDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class ResourceEmployeeOptionDescriptor:
    value: str
    label: str
    name: str
    title: str
    contact: str
    context: str
    is_active: bool


@dataclass(frozen=True)
class ResourceDesktopDto:
    id: str
    name: str
    role: str
    worker_type: str
    worker_type_label: str
    cost_type: str
    cost_type_label: str
    hourly_rate: float
    hourly_rate_label: str
    currency_code: str | None
    capacity_percent: float
    capacity_label: str
    address: str
    contact: str
    employee_id: str | None
    employee_context: str
    is_active: bool
    active_label: str
    version: int


@dataclass(frozen=True)
class ResourceCreateCommand:
    name: str = ""
    role: str = ""
    hourly_rate: float = 0.0
    is_active: bool = True
    cost_type: str = CostType.LABOR.value
    currency_code: str | None = None
    capacity_percent: float = 100.0
    address: str = ""
    contact: str = ""
    worker_type: str = WorkerType.EXTERNAL.value
    employee_id: str | None = None


@dataclass(frozen=True)
class ResourceUpdateCommand:
    resource_id: str
    name: str = ""
    role: str = ""
    hourly_rate: float = 0.0
    is_active: bool = True
    cost_type: str = CostType.LABOR.value
    currency_code: str | None = None
    capacity_percent: float = 100.0
    address: str = ""
    contact: str = ""
    worker_type: str = WorkerType.EXTERNAL.value
    employee_id: str | None = None
    expected_version: int | None = None


class ProjectManagementResourcesDesktopApi:
    def __init__(
        self,
        *,
        resource_service: ResourceService | None = None,
        employee_service: EmployeeService | None = None,
    ) -> None:
        self._resource_service = resource_service
        self._employee_service = employee_service

    def list_worker_types(self) -> tuple[ResourceWorkerTypeDescriptor, ...]:
        return tuple(
            ResourceWorkerTypeDescriptor(
                value=worker_type.value,
                label=_format_enum_label(worker_type.value),
            )
            for worker_type in WorkerType
        )

    def list_categories(self) -> tuple[ResourceCategoryDescriptor, ...]:
        return tuple(
            ResourceCategoryDescriptor(
                value=cost_type.value,
                label=_format_enum_label(cost_type.value),
            )
            for cost_type in CostType
        )

    def list_employees(self) -> tuple[ResourceEmployeeOptionDescriptor, ...]:
        if self._employee_service is None:
            return ()
        try:
            employees = sorted(
                self._employee_service.list_employees(active_only=None),
                key=lambda employee: (
                    not bool(getattr(employee, "is_active", True)),
                    str(getattr(employee, "full_name", "") or "").casefold(),
                    str(getattr(employee, "employee_code", "") or "").casefold(),
                ),
            )
        except Exception:
            return ()
        return tuple(
            ResourceEmployeeOptionDescriptor(
                value=employee.id,
                label=_employee_option_label(employee),
                name=employee.full_name,
                title=(employee.title or "").strip(),
                contact=_employee_contact(employee),
                context=_employee_context(employee),
                is_active=bool(getattr(employee, "is_active", True)),
            )
            for employee in employees
            if getattr(employee, "id", None)
        )

    def list_resources(self) -> tuple[ResourceDesktopDto, ...]:
        if self._resource_service is None:
            return ()
        employee_lookup = {
            option.value: option
            for option in self.list_employees()
        }
        resources = sorted(
            self._resource_service.list_resources(),
            key=lambda resource: (
                not bool(getattr(resource, "is_active", True)),
                str(getattr(resource, "name", "") or "").casefold(),
            ),
        )
        return tuple(
            self._serialize_resource(resource, employee_lookup=employee_lookup)
            for resource in resources
        )

    def create_resource(self, command: ResourceCreateCommand) -> ResourceDesktopDto:
        service = self._require_resource_service()
        resource = service.create_resource(
            name=command.name,
            role=command.role,
            hourly_rate=command.hourly_rate,
            is_active=command.is_active,
            cost_type=_coerce_cost_type(command.cost_type),
            currency_code=command.currency_code,
            capacity_percent=command.capacity_percent,
            address=command.address,
            contact=command.contact,
            worker_type=_coerce_worker_type(command.worker_type),
            employee_id=command.employee_id,
        )
        return self._serialize_resource(
            resource,
            employee_lookup=self._employee_lookup(),
        )

    def update_resource(self, command: ResourceUpdateCommand) -> ResourceDesktopDto:
        service = self._require_resource_service()
        resource = service.update_resource(
            command.resource_id,
            name=command.name,
            role=command.role,
            hourly_rate=command.hourly_rate,
            is_active=command.is_active,
            cost_type=_coerce_cost_type(command.cost_type),
            currency_code=command.currency_code,
            capacity_percent=command.capacity_percent,
            address=command.address,
            contact=command.contact,
            worker_type=_coerce_worker_type(command.worker_type),
            employee_id=command.employee_id,
            expected_version=command.expected_version,
        )
        return self._serialize_resource(
            resource,
            employee_lookup=self._employee_lookup(),
        )

    def toggle_resource_active(
        self,
        resource_id: str,
        *,
        expected_version: int | None = None,
    ) -> ResourceDesktopDto:
        service = self._require_resource_service()
        resource = service.get_resource(resource_id)
        updated = service.update_resource(
            resource_id,
            is_active=not bool(getattr(resource, "is_active", True)),
            expected_version=expected_version,
        )
        return self._serialize_resource(
            updated,
            employee_lookup=self._employee_lookup(),
        )

    def delete_resource(self, resource_id: str) -> None:
        self._require_resource_service().delete_resource(resource_id)

    def _require_resource_service(self) -> ResourceService:
        if self._resource_service is None:
            raise RuntimeError("Project management resources desktop API is not connected.")
        return self._resource_service

    def _employee_lookup(self) -> dict[str, ResourceEmployeeOptionDescriptor]:
        return {
            option.value: option
            for option in self.list_employees()
        }

    @staticmethod
    def _serialize_resource(
        resource,
        *,
        employee_lookup: dict[str, ResourceEmployeeOptionDescriptor],
    ) -> ResourceDesktopDto:
        employee_id = str(getattr(resource, "employee_id", "") or "").strip() or None
        employee_option = employee_lookup.get(employee_id or "")
        resolved_currency = (getattr(resource, "currency_code", None) or "").strip().upper() or None
        worker_type = _coerce_worker_type(getattr(resource, "worker_type", None))
        cost_type = _coerce_cost_type(getattr(resource, "cost_type", None))
        employee_context = (
            employee_option.context
            if employee_option is not None
            else "-"
        )
        return ResourceDesktopDto(
            id=resource.id,
            name=resource.name,
            role=getattr(resource, "role", "") or "",
            worker_type=worker_type.value,
            worker_type_label=_format_enum_label(worker_type.value),
            cost_type=cost_type.value,
            cost_type_label=_format_enum_label(cost_type.value),
            hourly_rate=float(getattr(resource, "hourly_rate", 0.0) or 0.0),
            hourly_rate_label=_format_money(
                getattr(resource, "hourly_rate", 0.0),
                resolved_currency,
            ),
            currency_code=resolved_currency,
            capacity_percent=float(getattr(resource, "capacity_percent", 100.0) or 100.0),
            capacity_label=f"{float(getattr(resource, 'capacity_percent', 100.0) or 100.0):.1f}%",
            address=(getattr(resource, "address", "") or "").strip(),
            contact=(getattr(resource, "contact", "") or "").strip(),
            employee_id=employee_id,
            employee_context=employee_context,
            is_active=bool(getattr(resource, "is_active", True)),
            active_label="Active" if bool(getattr(resource, "is_active", True)) else "Inactive",
            version=int(getattr(resource, "version", 1) or 1),
        )


def build_project_management_resources_desktop_api(
    *,
    resource_service: ResourceService | None = None,
    employee_service: EmployeeService | None = None,
) -> ProjectManagementResourcesDesktopApi:
    return ProjectManagementResourcesDesktopApi(
        resource_service=resource_service,
        employee_service=employee_service,
    )


def _coerce_cost_type(value: str | CostType | None) -> CostType:
    if isinstance(value, CostType):
        return value
    normalized_value = str(value or CostType.LABOR.value).strip().upper()
    try:
        return CostType(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported resource category: {normalized_value}.") from exc


def _coerce_worker_type(value: str | WorkerType | None) -> WorkerType:
    if isinstance(value, WorkerType):
        return value
    normalized_value = str(value or WorkerType.EXTERNAL.value).strip().upper()
    try:
        return WorkerType(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported worker type: {normalized_value}.") from exc


def _format_enum_label(value: str) -> str:
    return value.replace("_", " ").title()


def _format_money(value: float | None, currency: str | None) -> str:
    amount = float(value or 0.0)
    resolved_currency = (currency or "").strip().upper()
    if resolved_currency:
        return f"{resolved_currency} {amount:,.2f}"
    return f"{amount:,.2f}"


def _employee_context(employee) -> str:
    parts = [
        str(getattr(employee, "department", "") or "").strip(),
        str(getattr(employee, "site_name", "") or "").strip(),
    ]
    values = [part for part in parts if part]
    return " | ".join(values) if values else "-"


def _employee_contact(employee) -> str:
    return (
        getattr(employee, "email", None)
        or getattr(employee, "phone", None)
        or ""
    ).strip()


def _employee_option_label(employee) -> str:
    label = (
        f"{str(getattr(employee, 'employee_code', '') or '').strip()} - "
        f"{str(getattr(employee, 'full_name', '') or '').strip()}"
    )
    context = _employee_context(employee)
    if context != "-":
        label += f" [{context}]"
    if not bool(getattr(employee, "is_active", True)):
        label += " (Inactive)"
    return label


__all__ = [
    "ProjectManagementResourcesDesktopApi",
    "ResourceCategoryDescriptor",
    "ResourceCreateCommand",
    "ResourceDesktopDto",
    "ResourceEmployeeOptionDescriptor",
    "ResourceUpdateCommand",
    "ResourceWorkerTypeDescriptor",
    "build_project_management_resources_desktop_api",
]
