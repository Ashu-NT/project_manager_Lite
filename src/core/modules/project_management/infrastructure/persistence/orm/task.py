"""Task ORM rows."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Date, Enum as SAEnum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.infra.persistence.orm.base import Base


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
        SAEnum(TaskStatus),
        default=TaskStatus.TODO,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(default=0)
    percent_complete: Mapped[float] = mapped_column(Float, default=0.0)
    actual_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_tasks_project_id", TaskORM.project_id)


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
    hours_logged: Mapped[float] = mapped_column(Float, default=0.0)
    project_resource_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("project_resources.id", ondelete="CASCADE"),
        nullable=True,
    )


Index("idx_task_assignments_project_resource", TaskAssignmentORM.project_resource_id)


class TaskDependencyORM(Base):
    __tablename__ = "task_dependencies"

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


Index("idx_dep_predecessor", TaskDependencyORM.predecessor_task_id)
Index("idx_dep_successor", TaskDependencyORM.successor_task_id)


