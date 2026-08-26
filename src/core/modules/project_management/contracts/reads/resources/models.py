from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from src.core.modules.project_management.contracts.reads.sorting import ReadSort


@dataclass(frozen=True, slots=True)
class ResourceCatalogReadItem:
    resource_id: str
    code: str
    name: str
    role: str
    worker_type: str
    cost_type: str
    is_active: bool
    capacity_percent: float
    organization_id: str
    kind: str = "PERSON"
    organization_label: str = ""
    department_id: str | None = None
    employee_name: str = ""
    employee_title: str = ""
    department_label: str = ""
    site_id: str | None = None
    site_label: str = ""
    employee_id: str | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class ResourceInspectorFact:
    resource_id: str
    code: str
    name: str
    role: str
    worker_type: str
    is_active: bool
    capacity_percent: float
    organization_id: str
    kind: str = "PERSON"
    organization_label: str = ""
    department_id: str | None = None
    department_label: str = ""
    site_id: str | None = None
    site_label: str = ""
    employee_id: str | None = None
    employee_name: str = ""
    project_count: int = 0
    assignment_count: int = 0
    version: int = 1
    can_read: bool = False
    can_manage: bool = False
    can_deactivate: bool = False
    can_reactivate: bool = False


@dataclass(frozen=True, slots=True)
class ResourceSummaryFact:
    resource_id: str
    code: str
    name: str
    role: str
    worker_type: str
    cost_type: str
    hourly_rate: Decimal
    currency_code: str | None
    is_active: bool
    capacity_percent: float
    address: str
    contact: str
    organization_id: str
    kind: str = "PERSON"
    organization_label: str = ""
    department_id: str | None = None
    department_label: str = ""
    site_id: str | None = None
    site_label: str = ""
    employee_id: str | None = None
    employee_name: str = ""
    employee_title: str = ""
    version: int = 1
    can_read: bool = False
    can_manage: bool = False


@dataclass(frozen=True, slots=True)
class ResourceCatalogSummary:
    total: int = 0
    active: int = 0
    employees: int = 0
    external: int = 0
    average_capacity: float = 0.0


@dataclass(frozen=True, slots=True)
class ResourceCatalogReadPage:
    items: tuple[ResourceCatalogReadItem, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    summary: ResourceCatalogSummary = ResourceCatalogSummary()
    sort: ReadSort = ReadSort("catalog")


@dataclass(frozen=True, slots=True)
class ResourceProjectFact:
    project_resource_id: str
    resource_id: str
    project_id: str
    project_code: str
    project_name: str
    project_status: str
    planned_hours: Decimal
    is_active: bool
    start_date: date | None
    end_date: date | None
    version: int
    can_open_project: bool = True


@dataclass(frozen=True, slots=True)
class ResourceProjectReadPage:
    items: tuple[ResourceProjectFact, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("projectName")


@dataclass(frozen=True, slots=True)
class ResourceAssignmentFact:
    assignment_id: str
    resource_id: str
    project_id: str
    project_code: str
    project_name: str
    task_id: str
    task_code: str
    task_name: str
    task_status: str
    scheduled_start: date | None
    scheduled_finish: date | None
    allocated_planned_hours: Decimal
    allocation_percent: Decimal
    actual_hours: Decimal
    actual_hours_source: str
    response_status: str
    project_resource_id: str | None
    assignment_version: int
    can_open_project: bool = True
    can_open_task: bool = True


@dataclass(frozen=True, slots=True)
class ResourceAssignmentReadPage:
    items: tuple[ResourceAssignmentFact, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("scheduledStart")


@dataclass(frozen=True, slots=True)
class ResourceActivityFact:
    activity_id: str
    resource_id: str
    occurred_at: datetime
    event_type: str
    category: str
    actor_label: str
    summary: str
    source_type: str
    source_id: str | None
    project_id: str | None
    task_id: str | None
    can_open_source: bool = False


@dataclass(frozen=True, slots=True)
class ResourceActivityReadPage:
    items: tuple[ResourceActivityFact, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("occurredAt")


@dataclass(frozen=True, slots=True)
class ResourceSkillFact:
    skill_id: str
    resource_id: str
    skill_code: str
    skill_name: str
    proficiency: str
    notes: str
    version: int


@dataclass(frozen=True, slots=True)
class ResourceSkillReadPage:
    items: tuple[ResourceSkillFact, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("skillName")


@dataclass(frozen=True, slots=True)
class ResourceCertificationFact:
    certification_id: str
    resource_id: str
    certification_code: str
    certification_name: str
    issued_date: date | None
    expiry_date: date | None
    certificate_number: str
    issuer: str
    notes: str
    cert_status: str
    version: int


@dataclass(frozen=True, slots=True)
class ResourceCertificationReadPage:
    items: tuple[ResourceCertificationFact, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("certificationName")


__all__ = [
    "ResourceCatalogReadItem",
    "ResourceCatalogReadPage",
    "ResourceCatalogSummary",
    "ResourceActivityFact",
    "ResourceActivityReadPage",
    "ResourceAssignmentFact",
    "ResourceAssignmentReadPage",
    "ResourceInspectorFact",
    "ResourceProjectFact",
    "ResourceProjectReadPage",
    "ResourceCertificationFact",
    "ResourceCertificationReadPage",
    "ResourceSkillFact",
    "ResourceSkillReadPage",
    "ResourceSummaryFact",
]
