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
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    submitted_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    submitted_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    approved_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)


Index("idx_baseline_project", ProjectBaselineORM.project_id)
Index("idx_baseline_created", ProjectBaselineORM.created_at)
Index("idx_baseline_status", ProjectBaselineORM.status)
Index("idx_baseline_project_status", ProjectBaselineORM.project_id, ProjectBaselineORM.status)


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


class BaselineVarianceRecordORM(Base):
    __tablename__ = "baseline_variance_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    new_baseline_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("project_baselines.id", ondelete="CASCADE"),
        nullable=False,
    )
    superseded_baseline_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("project_baselines.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    task_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    start_variance_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    finish_variance_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_variance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[date] = mapped_column(Date, nullable=False)


Index("idx_variance_new_baseline", BaselineVarianceRecordORM.new_baseline_id)
Index("idx_variance_superseded", BaselineVarianceRecordORM.superseded_baseline_id)
Index("idx_variance_project", BaselineVarianceRecordORM.project_id)
Index("idx_variance_task", BaselineVarianceRecordORM.task_id)
