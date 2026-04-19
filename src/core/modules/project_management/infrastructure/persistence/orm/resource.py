"""Resource ORM rows."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Enum as SAEnum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.modules.project_management.domain.enums import CostType, WorkerType
from src.infra.persistence.orm.base import Base


class ResourceORM(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="")
    hourly_rate: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    capacity_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
        server_default="100.0",
    )
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cost_type: Mapped[CostType] = mapped_column(
        SAEnum(CostType),
        default=CostType.LABOR,
        nullable=False,
    )
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


Index("idx_resources_employee", ResourceORM.employee_id)
