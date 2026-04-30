"""Project ORM rows."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Enum as SAEnum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.modules.project_management.domain.enums import ProjectStatus
from src.infra.persistence.orm.base import Base


class ProjectORM(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="")
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus),
        default=ProjectStatus.PLANNED,
        nullable=False,
    )
    client_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    client_contact: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    planned_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class ProjectResourceORM(Base):
    __tablename__ = "project_resources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    hourly_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    planned_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


Index("idx_project_resource_project", ProjectResourceORM.project_id)
Index("idx_project_resource_resource", ProjectResourceORM.resource_id)
Index(
    "ux_project_resource_project_resource",
    ProjectResourceORM.project_id,
    ProjectResourceORM.resource_id,
    unique=True,
)
