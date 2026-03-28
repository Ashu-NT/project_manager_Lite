# infra/platform/db/models.py
from __future__ import annotations
from datetime import date,datetime
from typing import Optional

from sqlalchemy import DateTime

from sqlalchemy import (
    String,
    Date,
    Float,
    Boolean,
    ForeignKey,
    Enum as SAEnum,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from infra.platform.db.base import Base
from core.modules.project_management.domain.enums import (
    CostType,
    DependencyType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)
from core.platform.org.domain import EmploymentType
from core.modules.project_management.domain.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from core.platform.time.domain import TimesheetPeriodStatus
from infra.platform.db.inventory_models import (
    InventoryItemCategoryORM,
    PurchaseOrderLineORM,
    PurchaseOrderORM,
    PurchaseRequisitionLineORM,
    PurchaseRequisitionORM,
    ReceiptHeaderORM,
    ReceiptLineORM,
    StockBalanceORM,
    StockItemORM,
    StockReservationORM,
    StockTransactionORM,
    StoreroomORM,
)


class ProjectORM(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="")
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus), default=ProjectStatus.PLANNED, nullable=False
    )
    
    client_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    client_contact: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    planned_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True) #' EUR, USD, etc.'
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class TaskORM(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="")
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    duration_days: Mapped[Optional[int]] = mapped_column(nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus), default=TaskStatus.TODO, nullable=False
    )
    priority: Mapped[int] = mapped_column(default=0)

    percent_complete: Mapped[float] = mapped_column(Float, default=0.0)
    actual_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
Index("idx_tasks_project_id", TaskORM.project_id)

class ResourceORM(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="")
    hourly_rate: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    capacity_percent: Mapped[float] = mapped_column(Float, nullable=False, default=100.0, server_default="100.0")
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    cost_type: Mapped[CostType] = mapped_column(SAEnum(CostType), default=CostType.LABOR, nullable=False)
    currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    worker_type: Mapped[WorkerType] = mapped_column(
        SAEnum(WorkerType),
        nullable=False,
        default=WorkerType.EXTERNAL,
        server_default=WorkerType.EXTERNAL.value,
    )
    employee_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class EmployeeORM(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    department_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    department: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    site_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
    )
    site_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        SAEnum(EmploymentType),
        nullable=False,
        default=EmploymentType.FULL_TIME,
        server_default=EmploymentType.FULL_TIME.value,
    )
    email: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class OrganizationORM(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    timezone_name: Mapped[str] = mapped_column(String(128), nullable=False, default="UTC", server_default="UTC")
    base_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR", server_default="EUR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class SiteORM(Base):
    __tablename__ = "sites"
    __table_args__ = (
        UniqueConstraint("organization_id", "site_code", name="ux_sites_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    site_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    address_line_1: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    address_line_2: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    site_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    default_calendar_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    default_language: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class DepartmentORM(Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("organization_id", "department_code", name="ux_departments_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    site_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_department_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    cost_center_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    manager_employee_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class DocumentORM(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("organization_id", "document_code", name="ux_documents_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_system: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    uploaded_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    review_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    confidentiality_level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    revision: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class DocumentLinkORM(Base):
    __tablename__ = "document_links"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "module_code",
            "entity_type",
            "entity_id",
            "link_role",
            name="ux_document_links_unique",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    module_code: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    link_role: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class PartyORM(Base):
    __tablename__ = "parties"
    __table_args__ = (
        UniqueConstraint("organization_id", "party_code", name="ux_parties_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    party_code: Mapped[str] = mapped_column(String(64), nullable=False)
    party_name: Mapped[str] = mapped_column(String(256), nullable=False)
    party_type: Mapped[str] = mapped_column(String(64), nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    address_line_1: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    address_line_2: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    tax_registration_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    external_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class ModuleEntitlementORM(Base):
    __tablename__ = "organization_module_entitlements"

    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    module_code: Mapped[str] = mapped_column(String(128), primary_key=True)
    licensed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    lifecycle_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="inactive",
        server_default="inactive",
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TaskAssignmentORM(Base):
    __tablename__ = "task_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.id",ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[str] = mapped_column(String, ForeignKey("resources.id",ondelete="CASCADE"), nullable=False)
    allocation_percent: Mapped[float] = mapped_column(Float, default=100.0)
    hours_logged: Mapped[float] = mapped_column(Float, default=0.0)
    project_resource_id: Mapped[Optional[str]] = mapped_column(
        String, 
        ForeignKey("project_resources.id",ondelete="CASCADE"), 
        nullable=True
    )

Index("idx_task_assignments_project_resource", TaskAssignmentORM.project_resource_id)


class TimeEntryORM(Base):
    __tablename__ = "time_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    assignment_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("task_assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False, default="task_assignment", server_default="task_assignment")
    owner_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    employee_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    site_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
    )
    site_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    author_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    author_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_time_entries_assignment", TimeEntryORM.assignment_id)
Index("idx_time_entries_date", TimeEntryORM.entry_date)
Index("idx_time_entries_owner", TimeEntryORM.owner_type, TimeEntryORM.owner_id)
Index("idx_time_entries_employee", TimeEntryORM.employee_id)
Index("idx_time_entries_department", TimeEntryORM.department_id)
Index("idx_time_entries_site", TimeEntryORM.site_id)


class TimesheetPeriodORM(Base):
    __tablename__ = "timesheet_periods"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[TimesheetPeriodStatus] = mapped_column(
        SAEnum(TimesheetPeriodStatus),
        nullable=False,
        default=TimesheetPeriodStatus.OPEN,
        server_default=TimesheetPeriodStatus.OPEN.value,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    submitted_by_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    submitted_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    decided_by_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


Index("idx_timesheet_periods_resource", TimesheetPeriodORM.resource_id)
Index("ux_timesheet_periods_resource_start", TimesheetPeriodORM.resource_id, TimesheetPeriodORM.period_start, unique=True)
Index("idx_sites_organization", SiteORM.organization_id)
Index("idx_sites_active", SiteORM.organization_id, SiteORM.is_active)
Index("idx_employees_department", EmployeeORM.department_id)
Index("idx_employees_site", EmployeeORM.site_id)
Index("idx_departments_organization", DepartmentORM.organization_id)
Index("idx_departments_active", DepartmentORM.organization_id, DepartmentORM.is_active)
Index("idx_departments_site", DepartmentORM.site_id)
Index("idx_departments_manager", DepartmentORM.manager_employee_id)
Index("idx_documents_organization", DocumentORM.organization_id)
Index("idx_documents_uploaded_by", DocumentORM.uploaded_by_user_id)
Index("idx_document_links_document", DocumentLinkORM.document_id)
Index("idx_document_links_entity", DocumentLinkORM.organization_id, DocumentLinkORM.module_code, DocumentLinkORM.entity_type, DocumentLinkORM.entity_id)
Index("idx_parties_organization", PartyORM.organization_id)
Index("idx_parties_active", PartyORM.organization_id, PartyORM.is_active)
Index("idx_parties_type", PartyORM.organization_id, PartyORM.party_type)

class TaskDependencyORM(Base):
    __tablename__ = "task_dependencies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    predecessor_task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.id",ondelete="CASCADE"), nullable=False)
    successor_task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.id",ondelete="CASCADE"), nullable=False)
    dependency_type: Mapped[DependencyType] = mapped_column(
        SAEnum(DependencyType), default=DependencyType.FINISH_TO_START, nullable=False
    )
    lag_days: Mapped[int] = mapped_column(nullable=False, default=0)
Index("idx_dep_predecessor", TaskDependencyORM.predecessor_task_id)
Index("idx_dep_successor", TaskDependencyORM.successor_task_id)

class CostItemORM(Base):
    __tablename__ = "cost_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id",ondelete="CASCADE"), nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("tasks.id",ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    cost_type: Mapped[str] = mapped_column(String, nullable=False, default="OVERHEAD")  # e.g. OVERHEAD, LABOR, MATERIAL
    currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True) #' EUR, USD, etc.'
    
    planned_amount: Mapped[float] = mapped_column(Float, nullable=False)
    committed_amount: Mapped[float] = mapped_column(Float, default=0.0)
    actual_amount: Mapped[float] = mapped_column(Float, default=0.0)
    incurred_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    
Index("idx_costs_project", CostItemORM.project_id)
Index("idx_costs_task", CostItemORM.task_id)
Index("idx_costs_type", CostItemORM.cost_type)

class CalendarEventORM(Base):
    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("projects.id",ondelete="CASCADE"), nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("tasks.id",ondelete="CASCADE"), nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(String, default="")
    
Index("idx_clandar_project", CalendarEventORM.project_id)
Index("idx_calendar_start_end", CalendarEventORM.start_date, CalendarEventORM.end_date )

class WorkingCalendarORM(Base):
    __tablename__ = "working_calendars"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # store working days as a comma-separated string, e.g. "0,1,2,3,4"
    working_days: Mapped[str] = mapped_column(String, nullable=False, default="0,1,2,3,4")
    hours_per_day: Mapped[float] = mapped_column(Float, default=8.0)


class HolidayORM(Base):
    __tablename__ = "holidays"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    calendar_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("working_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String, default="")

Index("idx_holiday_calendar_date", HolidayORM.calendar_id, HolidayORM.date)


class ProjectBaselineORM(Base):
    __tablename__ = "project_baselines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

Index("idx_baseline_project", ProjectBaselineORM.project_id)
Index("idx_baseline_created", ProjectBaselineORM.created_at)

class BaselineTaskORM(Base):
    __tablename__ = "baseline_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    baseline_id: Mapped[str] = mapped_column(String, ForeignKey("project_baselines.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    task_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    baseline_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    baseline_finish: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    baseline_duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    baseline_planned_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

Index("idx_baseline_task_baseline", BaselineTaskORM.baseline_id)
Index("idx_baseline_task_task", BaselineTaskORM.task_id)

class ProjectResourceORM(Base):
    __tablename__ = "project_resources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[str] = mapped_column(String, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    
    hourly_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    planned_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
Index("idx_project_resource_project", ProjectResourceORM.project_id)
Index("idx_project_resource_resource", ProjectResourceORM.resource_id)
Index("ux_project_resource_project_resource", ProjectResourceORM.project_id, ProjectResourceORM.resource_id, unique=True)


class RegisterEntryORM(Base):
    __tablename__ = "register_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_type: Mapped[RegisterEntryType] = mapped_column(SAEnum(RegisterEntryType), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    severity: Mapped[RegisterEntrySeverity] = mapped_column(
        SAEnum(RegisterEntrySeverity),
        nullable=False,
        default=RegisterEntrySeverity.MEDIUM,
        server_default=RegisterEntrySeverity.MEDIUM.value,
    )
    status: Mapped[RegisterEntryStatus] = mapped_column(
        SAEnum(RegisterEntryStatus),
        nullable=False,
        default=RegisterEntryStatus.OPEN,
        server_default=RegisterEntryStatus.OPEN.value,
    )
    owner_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    impact_summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    response_plan: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class UserORM(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("identity_provider", "federated_subject", name="ux_users_federated_identity"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    identity_provider: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    federated_subject: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    session_timeout_minutes_override: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    session_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    last_login_auth_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_login_device_label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    session_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class AuthSessionORM(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    auth_method: Mapped[str] = mapped_column(String(64), nullable=False)
    device_label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class RoleORM(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")


class PermissionORM(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")


class UserRoleORM(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="ux_user_roles_user_role"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)


class RolePermissionORM(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="ux_role_permissions_role_perm"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[str] = mapped_column(String, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)


class ProjectMembershipORM(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="ux_project_memberships_project_user"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_role: Mapped[str] = mapped_column(String(64), nullable=False, default="viewer", server_default="viewer")
    permission_codes_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ScopedAccessGrantORM(Base):
    __tablename__ = "scoped_access_grants"
    __table_args__ = (
        UniqueConstraint("scope_type", "scope_id", "user_id", name="ux_scoped_access_scope_user"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_role: Mapped[str] = mapped_column(String(64), nullable=False, default="viewer", server_default="viewer")
    permission_codes_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    actor_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")


class ApprovalRequestORM(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    request_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default="PENDING")
    requested_by_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    requested_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    decided_by_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class RuntimeExecutionORM(Base):
    __tablename__ = "runtime_executions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    operation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    module_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING", server_default="RUNNING")
    requested_by_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    requested_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    input_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TaskCommentORM(Base):
    __tablename__ = "task_comments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    author_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mentions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    mentioned_user_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    attachments_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    read_by_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    read_by_user_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TaskPresenceORM(Base):
    __tablename__ = "task_presence"
    __table_args__ = (
        UniqueConstraint("task_id", "username", name="ux_task_presence_task_username"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    activity: Mapped[str] = mapped_column(String(32), nullable=False, default="reviewing", server_default="reviewing")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class PortfolioScoringTemplateORM(Base):
    __tablename__ = "portfolio_scoring_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    strategic_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    value_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default="2")
    urgency_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default="2")
    risk_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class PortfolioIntakeItemORM(Base):
    __tablename__ = "portfolio_intake_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    sponsor_name: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    requested_budget: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    requested_capacity_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )
    target_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    strategic_score: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    value_score: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    urgency_score: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    scoring_template_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    scoring_template_name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        default="Balanced PMO",
        server_default="Balanced PMO",
    )
    strategic_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    value_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default="2")
    urgency_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default="2")
    risk_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PROPOSED", server_default="PROPOSED")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class PortfolioScenarioORM(Base):
    __tablename__ = "portfolio_scenarios"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    budget_limit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    capacity_limit_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    project_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    intake_item_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class PortfolioProjectDependencyORM(Base):
    __tablename__ = "portfolio_project_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "predecessor_project_id",
            "successor_project_id",
            name="ux_portfolio_project_dependencies_pair",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    predecessor_project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    successor_project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    dependency_type: Mapped[str] = mapped_column(String(8), nullable=False, default="FS", server_default="FS")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_register_entries_project", RegisterEntryORM.project_id)
Index("idx_register_entries_type", RegisterEntryORM.entry_type)
Index("idx_register_entries_status", RegisterEntryORM.status)
Index("idx_register_entries_due", RegisterEntryORM.due_date)
Index("idx_users_username", UserORM.username, unique=True)
Index("idx_auth_sessions_user", AuthSessionORM.user_id)
Index("idx_auth_sessions_expires", AuthSessionORM.expires_at)
Index("idx_auth_sessions_revoked", AuthSessionORM.revoked_at)
Index("idx_employees_code", EmployeeORM.employee_code, unique=True)
Index("idx_employees_active", EmployeeORM.is_active)
Index("idx_organizations_code", OrganizationORM.organization_code, unique=True)
Index("idx_organizations_active", OrganizationORM.is_active)
Index("idx_org_module_entitlements_org", ModuleEntitlementORM.organization_id)
Index("idx_resources_employee", ResourceORM.employee_id)
Index("idx_roles_name", RoleORM.name, unique=True)
Index("idx_permissions_code", PermissionORM.code, unique=True)
Index("idx_user_roles_user", UserRoleORM.user_id)
Index("idx_user_roles_role", UserRoleORM.role_id)
Index("idx_role_permissions_role", RolePermissionORM.role_id)
Index("idx_role_permissions_permission", RolePermissionORM.permission_id)
Index("idx_project_memberships_project", ProjectMembershipORM.project_id)
Index("idx_project_memberships_user", ProjectMembershipORM.user_id)
Index("idx_scoped_access_scope", ScopedAccessGrantORM.scope_type, ScopedAccessGrantORM.scope_id)
Index("idx_scoped_access_user", ScopedAccessGrantORM.user_id)
Index("idx_audit_logs_occurred_at", AuditLogORM.occurred_at)
Index("idx_audit_logs_project", AuditLogORM.project_id)
Index("idx_audit_logs_entity", AuditLogORM.entity_type, AuditLogORM.entity_id)
Index("idx_approval_status", ApprovalRequestORM.status)
Index("idx_approval_project", ApprovalRequestORM.project_id)
Index("idx_approval_type", ApprovalRequestORM.request_type)
Index("idx_runtime_executions_started", RuntimeExecutionORM.started_at)
Index("idx_runtime_executions_module_status", RuntimeExecutionORM.module_code, RuntimeExecutionORM.status)
Index("idx_task_comments_task", TaskCommentORM.task_id)
Index("idx_task_comments_created", TaskCommentORM.created_at)
Index("idx_task_presence_task", TaskPresenceORM.task_id)
Index("idx_task_presence_seen", TaskPresenceORM.last_seen_at)
Index("idx_portfolio_scoring_active", PortfolioScoringTemplateORM.is_active)
Index("idx_portfolio_scoring_updated", PortfolioScoringTemplateORM.updated_at)
Index("idx_portfolio_intake_status", PortfolioIntakeItemORM.status)
Index("idx_portfolio_intake_updated", PortfolioIntakeItemORM.updated_at)
Index("idx_portfolio_intake_template", PortfolioIntakeItemORM.scoring_template_id)
Index("idx_portfolio_scenarios_updated", PortfolioScenarioORM.updated_at)
Index("idx_portfolio_project_dependencies_predecessor", PortfolioProjectDependencyORM.predecessor_project_id)
Index("idx_portfolio_project_dependencies_successor", PortfolioProjectDependencyORM.successor_project_id)
