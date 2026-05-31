from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.core.modules.project_management.application.resources import ResourceAvailabilityService, ResourceService
from src.core.modules.project_management.application.scheduling.work_calendar_engine import WorkCalendarEngine
from src.core.modules.project_management.contracts.repositories.task import AssignmentRepository
from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.domain.resources.skills import SkillProficiencyLevel
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


@dataclass(frozen=True)
class ResourceSkillDesktopDto:
    id: str
    resource_id: str
    skill_code: str
    skill_name: str
    proficiency: str
    proficiency_label: str
    notes: str


@dataclass(frozen=True)
class ResourceCertificationDesktopDto:
    id: str
    resource_id: str
    certification_code: str
    certification_name: str
    issued_date: Optional[str]
    expiry_date: Optional[str]
    issuing_body: str
    notes: str
    cert_status: str


@dataclass(frozen=True)
class ResourceAvailabilityDayDto:
    date_label: str
    allocation_percent: float
    allocation_label: str
    overloaded: bool


@dataclass(frozen=True)
class ResourceAvailabilityDto:
    resource_id: str
    peak_load_percent: float
    average_load_percent: float
    overloaded_days: int
    available_days: int
    is_available: bool
    from_date_label: str
    to_date_label: str
    days: tuple[ResourceAvailabilityDayDto, ...]


@dataclass(frozen=True)
class ResourceAddSkillCommand:
    resource_id: str
    skill_code: str
    skill_name: str
    proficiency: str = "intermediate"
    notes: str = ""


@dataclass(frozen=True)
class ResourceAddCertificationCommand:
    resource_id: str
    certification_code: str
    certification_name: str
    issued_date: Optional[str] = None
    expiry_date: Optional[str] = None
    issuing_body: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ResourceAssignmentDesktopDto:
    id: str
    task_id: str
    task_name: str
    project_id: str
    project_name: str
    allocation_percent: float
    hours_logged: float
    allocation_label: str
    hours_label: str


class ProjectManagementResourcesDesktopApi:
    def __init__(
        self,
        *,
        resource_service: ResourceService | None = None,
        employee_service: EmployeeService | None = None,
        availability_service: ResourceAvailabilityService | None = None,
        task_service: object | None = None,
        assignment_repo: AssignmentRepository | None = None,
        project_service: object | None = None,
        work_calendar_engine: WorkCalendarEngine | None = None,
    ) -> None:
        self._resource_service = resource_service
        self._employee_service = employee_service
        self._availability_service = availability_service
        self._task_service = task_service
        self._assignment_repo = assignment_repo
        self._project_service = project_service
        self._work_calendar_engine = work_calendar_engine

    def _get_availability_service(self) -> ResourceAvailabilityService | None:
        if self._availability_service is not None:
            return self._availability_service
        # Build from injected components when the service wasn't registered
        assignment_repo = self._assignment_repo
        resource_repo = (
            getattr(self._resource_service, "_resource_repo", None)
            or getattr(self._task_service, "_resource_repo", None)
        )
        task_repo = getattr(self._task_service, "_task_repo", None)
        calendar = (
            self._work_calendar_engine
            or getattr(self._task_service, "_work_calendar_engine", None)
            or getattr(self._task_service, "_calendar", None)
        )
        if assignment_repo and resource_repo and task_repo and calendar:
            return ResourceAvailabilityService(
                resource_repo=resource_repo,
                assignment_repo=assignment_repo,
                task_repo=task_repo,
                calendar=calendar,
            )
        return None

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

    def list_resource_skills(self, resource_id: str) -> tuple[ResourceSkillDesktopDto, ...]:
        service = self._resource_service
        if service is None:
            return ()
        try:
            skills = service.list_resource_skills(resource_id)
        except Exception:
            return ()
        return tuple(self._serialize_skill(s) for s in skills)

    def list_resource_certifications(self, resource_id: str) -> tuple[ResourceCertificationDesktopDto, ...]:
        service = self._resource_service
        if service is None:
            return ()
        try:
            certs = service.list_resource_certifications(resource_id)
        except Exception:
            return ()
        return tuple(self._serialize_cert(c) for c in certs)

    def add_resource_skill(self, command: ResourceAddSkillCommand) -> ResourceSkillDesktopDto:
        service = self._require_resource_service()
        skill = service.add_resource_skill(
            resource_id=command.resource_id,
            skill_code=command.skill_code,
            skill_name=command.skill_name,
            proficiency=command.proficiency,
            notes=command.notes,
        )
        return self._serialize_skill(skill)

    def remove_resource_skill(self, skill_id: str) -> None:
        self._require_resource_service().remove_resource_skill(skill_id)

    def add_resource_certification(self, command: ResourceAddCertificationCommand) -> ResourceCertificationDesktopDto:
        service = self._require_resource_service()
        issued = _parse_date(command.issued_date)
        expiry = _parse_date(command.expiry_date)
        cert = service.add_resource_certification(
            resource_id=command.resource_id,
            certification_code=command.certification_code,
            certification_name=command.certification_name,
            issued_date=issued,
            expiry_date=expiry,
            issuing_body=command.issuing_body,
            notes=command.notes,
        )
        return self._serialize_cert(cert)

    def remove_resource_certification(self, cert_id: str) -> None:
        self._require_resource_service().remove_resource_certification(cert_id)

    def _require_resource_service(self) -> ResourceService:
        if self._resource_service is None:
            raise RuntimeError("Project management resources desktop API is not connected.")
        return self._resource_service

    @staticmethod
    def _serialize_skill(skill) -> ResourceSkillDesktopDto:
        proficiency_raw = str(getattr(skill, "proficiency", "") or "intermediate")
        if hasattr(proficiency_raw, "value"):
            proficiency_raw = proficiency_raw.value
        return ResourceSkillDesktopDto(
            id=skill.id,
            resource_id=skill.resource_id,
            skill_code=skill.skill_code,
            skill_name=skill.skill_name,
            proficiency=proficiency_raw,
            proficiency_label=proficiency_raw.replace("_", " ").title(),
            notes=skill.notes or "",
        )

    @staticmethod
    def _serialize_cert(cert) -> ResourceCertificationDesktopDto:
        from datetime import date as _date
        today = _date.today()
        expiry = getattr(cert, "expiry_date", None)
        issued = getattr(cert, "issued_date", None)
        if expiry is None:
            status = "valid"
        elif expiry < today:
            status = "expired"
        elif (expiry - today).days <= 30:
            status = "expiring-soon"
        else:
            status = "valid"
        return ResourceCertificationDesktopDto(
            id=cert.id,
            resource_id=cert.resource_id,
            certification_code=cert.certification_code,
            certification_name=cert.certification_name,
            issued_date=issued.isoformat() if issued else None,
            expiry_date=expiry.isoformat() if expiry else None,
            issuing_body=cert.issuing_body or "",
            notes=cert.notes or "",
            cert_status=status,
        )

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


    def list_resource_assignments(self, resource_id: str) -> tuple[ResourceAssignmentDesktopDto, ...]:
        normalized_id = str(resource_id or "").strip()
        if not normalized_id:
            return ()

        # Get assignment repo: primary is the injected repo, fallback via availability service
        repo = self._assignment_repo
        if repo is None and self._availability_service is not None:
            repo = getattr(self._availability_service, "_assignments", None)
        if repo is None:
            return ()

        list_by_resource = getattr(repo, "list_by_resource", None)
        if not callable(list_by_resource):
            return ()
        try:
            assignments = list(list_by_resource(normalized_id))
        except Exception:
            return ()

        if not assignments:
            return ()

        # Build task lookup using the task service's list_tasks_for_resource (one query)
        tasks_by_id: dict[str, object] = {}
        if self._task_service is not None:
            list_tasks_fn = getattr(self._task_service, "list_tasks_for_resource", None)
            if callable(list_tasks_fn):
                try:
                    for task in list_tasks_fn(normalized_id):
                        tasks_by_id[str(getattr(task, "id", "") or "")] = task
                except Exception:
                    pass

        # Build project name lookup from unique project IDs in the task set
        project_names: dict[str, str] = {}
        if self._project_service is not None:
            get_project = getattr(self._project_service, "get_project", None)
            for task in tasks_by_id.values():
                pid = str(getattr(task, "project_id", "") or "")
                if pid and pid not in project_names and callable(get_project):
                    try:
                        proj = get_project(pid)
                        if proj:
                            project_names[pid] = str(getattr(proj, "name", "") or pid)
                    except Exception:
                        project_names[pid] = pid

        results: list[ResourceAssignmentDesktopDto] = []
        for assignment in assignments:
            task_id = str(getattr(assignment, "task_id", "") or "")
            task = tasks_by_id.get(task_id)
            task_name = str(getattr(task, "name", "") or task_id) if task else task_id
            project_id = str(getattr(task, "project_id", "") or "") if task else ""
            project_name = project_names.get(project_id, project_id)

            alloc = float(getattr(assignment, "allocation_percent", 0.0) or 0.0)
            hours = float(getattr(assignment, "hours_logged", 0.0) or 0.0)
            results.append(ResourceAssignmentDesktopDto(
                id=str(getattr(assignment, "id", "") or ""),
                task_id=task_id,
                task_name=task_name,
                project_id=project_id,
                project_name=project_name,
                allocation_percent=alloc,
                hours_logged=hours,
                allocation_label=f"{alloc:.0f}%",
                hours_label=f"{hours:.1f} hrs",
            ))
        return tuple(results)

    def build_resource_availability(self, resource_id: str) -> ResourceAvailabilityDto | None:
        if not resource_id:
            return None
        svc = self._get_availability_service()
        if svc is None:
            return None
        from datetime import date as _date, timedelta
        today = _date.today()
        to_date = today + timedelta(days=90)
        try:
            report = svc.check_availability(
                resource_ids=[resource_id],
                from_date=today,
                to_date=to_date,
            )
        except Exception:
            return None
        window = next((r for r in report.resources if str(r.resource_id) == resource_id), None)
        if window is None:
            return None
        # Return ALL working days (not just overloaded) for timeline chart — cap at 90 days
        all_days = getattr(window, "daily_loads", []) or []
        return ResourceAvailabilityDto(
            resource_id=resource_id,
            peak_load_percent=float(window.peak_load_percent or 0.0),
            average_load_percent=float(window.average_load_percent or 0.0),
            overloaded_days=int(window.overloaded_days or 0),
            available_days=int(window.available_days or 0),
            is_available=bool(window.is_available),
            from_date_label=today.strftime("%d %b %Y"),
            to_date_label=to_date.strftime("%d %b %Y"),
            days=tuple(
                ResourceAvailabilityDayDto(
                    date_label=d.check_date.strftime("%d %b"),
                    allocation_percent=float(d.total_allocation_percent or 0.0),
                    allocation_label=f"{d.total_allocation_percent:.0f}%",
                    overloaded=bool(d.overloaded),
                )
                for d in all_days[:90]
            ),
        )


def build_project_management_resources_desktop_api(
    *,
    resource_service: ResourceService | None = None,
    employee_service: EmployeeService | None = None,
    availability_service: ResourceAvailabilityService | None = None,
    task_service: object | None = None,
    assignment_repo: AssignmentRepository | None = None,
    project_service: object | None = None,
    work_calendar_engine: WorkCalendarEngine | None = None,
) -> ProjectManagementResourcesDesktopApi:
    return ProjectManagementResourcesDesktopApi(
        resource_service=resource_service,
        employee_service=employee_service,
        availability_service=availability_service,
        task_service=task_service,
        assignment_repo=assignment_repo,
        project_service=project_service,
        work_calendar_engine=work_calendar_engine,
    )


def _parse_date(value: str | None) -> "date | None":
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except (ValueError, AttributeError):
        return None


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
    "ResourceAddCertificationCommand",
    "ResourceAddSkillCommand",
    "ResourceAssignmentDesktopDto",
    "ResourceCategoryDescriptor",
    "ResourceCertificationDesktopDto",
    "ResourceCreateCommand",
    "ResourceDesktopDto",
    "ResourceEmployeeOptionDescriptor",
    "ResourceSkillDesktopDto",
    "ResourceUpdateCommand",
    "ResourceWorkerTypeDescriptor",
    "build_project_management_resources_desktop_api",
]
