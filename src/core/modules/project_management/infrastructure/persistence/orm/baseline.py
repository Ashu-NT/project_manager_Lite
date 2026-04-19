"""Baseline ORM rows."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class ProjectBaselineORM(Base):
    __tablename__ = "project_baselines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_baseline_project", ProjectBaselineORM.project_id)
Index("idx_baseline_created", ProjectBaselineORM.created_at)


class BaselineTaskORM(Base):
    __tablename__ = "baseline_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    baseline_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("project_baselines.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    task_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    baseline_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    baseline_finish: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    baseline_duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    baseline_planned_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


Index("idx_baseline_task_baseline", BaselineTaskORM.baseline_id)
Index("idx_baseline_task_task", BaselineTaskORM.task_id)
