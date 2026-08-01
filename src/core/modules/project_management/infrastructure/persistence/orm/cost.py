"""Cost ORM rows."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class CostItemORM(Base):
    __tablename__ = "cost_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    cost_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    cost_type: Mapped[str] = mapped_column(String, nullable=False, default="OVERHEAD")
    currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    planned_amount: Mapped[float] = mapped_column(Float, nullable=False)
    committed_amount: Mapped[float] = mapped_column(Float, default=0.0)
    actual_amount: Mapped[float] = mapped_column(Float, default=0.0)
    forecast_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    commitment_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="uncommitted",
        server_default="uncommitted",
    )
    vendor_reference: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    incurred_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_costs_project", CostItemORM.project_id)
Index("ux_costs_project_code", CostItemORM.project_id, CostItemORM.cost_code, unique=True)
Index("idx_costs_task", CostItemORM.task_id)
Index("idx_costs_type", CostItemORM.cost_type)
Index("idx_costs_commitment_status", CostItemORM.commitment_status)

__all__ = ["CostItemORM"]
