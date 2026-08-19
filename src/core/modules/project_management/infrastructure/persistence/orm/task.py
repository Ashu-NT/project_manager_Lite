"""Task ORM rows."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.infra.persistence.db.financial_numeric import (
    FinancialNumericKind,
    financial_numeric,
    financial_numeric_info,
)
from src.infra.persistence.orm.base import Base


class TaskORM(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "parent_task_id IS NULL OR parent_task_id <> id",
            name="ck_tasks_wbs_parent_not_self",
        ),
        CheckConstraint("sort_order >= 0", name="ck_tasks_wbs_sort_order"),
        CheckConstraint(
            "length(wbs_code) >= 1 AND length(wbs_code) <= 64",
            name="ck_tasks_wbs_code_length",
        ),
        ForeignKeyConstraint(
            ["project_id", "parent_task_id"],
            ["tasks.project_id", "tasks.id"],
            name="fk_tasks_wbs_same_project_parent",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("project_id", "id", name="uq_tasks_project_id"),
        UniqueConstraint("project_id", "wbs_code", name="uq_tasks_project_wbs_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    parent_task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    wbs_code: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="")
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    duration_days: Mapped[Optional[int]] = mapped_column(nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus),
        default=TaskStatus.TODO,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(default=0)
    percent_complete: Mapped[float] = mapped_column(Float, default=0.0)
    actual_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    constraint_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    constraint_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_milestone: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    resource_leveling_not_before: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_tasks_project_id", TaskORM.project_id)
Index("ux_tasks_project_code", TaskORM.project_id, TaskORM.task_code, unique=True)
Index("idx_tasks_wbs_parent_order", TaskORM.project_id, TaskORM.parent_task_id, TaskORM.sort_order)


class TaskAssignmentORM(Base):
    __tablename__ = "task_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    allocation_percent: Mapped[float] = mapped_column(Float, default=100.0)
    hours_logged: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.QUANTITY),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
        info=financial_numeric_info(FinancialNumericKind.QUANTITY),
    )
    allocated_planned_hours: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.QUANTITY),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
        info=financial_numeric_info(FinancialNumericKind.QUANTITY),
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    project_resource_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("project_resources.id", ondelete="CASCADE"),
        nullable=True,
    )
    response_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


Index("idx_task_assignments_project_resource", TaskAssignmentORM.project_resource_id)
Index(
    "ux_task_assignments_task_resource",
    TaskAssignmentORM.task_id,
    TaskAssignmentORM.resource_id,
    unique=True,
)


class TaskDependencyORM(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        CheckConstraint(
            "predecessor_task_id <> successor_task_id",
            name="ck_task_dependencies_not_self",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    predecessor_task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    successor_task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    dependency_type: Mapped[DependencyType] = mapped_column(
        SAEnum(DependencyType),
        default=DependencyType.FINISH_TO_START,
        nullable=False,
    )
    lag_days: Mapped[int] = mapped_column(nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_dep_predecessor", TaskDependencyORM.predecessor_task_id)
Index("idx_dep_successor", TaskDependencyORM.successor_task_id)
Index(
    "ux_task_dependencies_pair",
    TaskDependencyORM.predecessor_task_id,
    TaskDependencyORM.successor_task_id,
    unique=True,
)
