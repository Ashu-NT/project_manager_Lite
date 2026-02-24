# infra/db/models.py
from __future__ import annotations
from datetime import date,datetime
from typing import Optional

from sqlalchemy import DateTime, Date

from sqlalchemy import (
    String,
    Date,
    Float,
    Boolean,
    ForeignKey,
    Enum as SAEnum,
    Index,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from core.models import (
    ProjectStatus,
    TaskStatus,
    DependencyType,
    CostType,
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
Index("idx_tasks_project_id", TaskORM.project_id)

class ResourceORM(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="")
    hourly_rate: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    cost_type: Mapped[CostType] = mapped_column(SAEnum(CostType), default=CostType.LABOR, nullable=False)
    currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)


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
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
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
