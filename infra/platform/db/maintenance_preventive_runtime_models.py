from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.modules.maintenance_management.domain import MaintenancePreventiveInstanceStatus
from infra.platform.db.base import Base


class MaintenancePreventivePlanInstanceORM(Base):
    __tablename__ = "maintenance_preventive_plan_instances"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "plan_id",
            "due_at",
            name="ux_maintenance_preventive_plan_instances_plan_due_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("maintenance_preventive_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_counter: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    status: Mapped[MaintenancePreventiveInstanceStatus] = mapped_column(
        SAEnum(MaintenancePreventiveInstanceStatus),
        nullable=False,
        default=MaintenancePreventiveInstanceStatus.PLANNED,
        server_default=MaintenancePreventiveInstanceStatus.PLANNED.value,
    )
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    generated_work_request_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_work_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    generated_work_order_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_work_orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_maintenance_preventive_instances_org", MaintenancePreventivePlanInstanceORM.organization_id)
Index("idx_maintenance_preventive_instances_plan", MaintenancePreventivePlanInstanceORM.plan_id)
Index("idx_maintenance_preventive_instances_due_at", MaintenancePreventivePlanInstanceORM.due_at)
Index("idx_maintenance_preventive_instances_status", MaintenancePreventivePlanInstanceORM.status)
Index(
    "idx_maintenance_preventive_instances_work_request",
    MaintenancePreventivePlanInstanceORM.generated_work_request_id,
)
Index(
    "idx_maintenance_preventive_instances_work_order",
    MaintenancePreventivePlanInstanceORM.generated_work_order_id,
)


__all__ = ["MaintenancePreventivePlanInstanceORM"]
