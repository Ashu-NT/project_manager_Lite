"""Portfolio ORM rows."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


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


Index("idx_portfolio_scoring_active", PortfolioScoringTemplateORM.is_active)
Index("idx_portfolio_scoring_updated", PortfolioScoringTemplateORM.updated_at)


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


Index("idx_portfolio_intake_status", PortfolioIntakeItemORM.status)
Index("idx_portfolio_intake_updated", PortfolioIntakeItemORM.updated_at)
Index("idx_portfolio_intake_template", PortfolioIntakeItemORM.scoring_template_id)


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


Index("idx_portfolio_scenarios_updated", PortfolioScenarioORM.updated_at)


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


Index("idx_portfolio_project_dependencies_predecessor", PortfolioProjectDependencyORM.predecessor_project_id)
Index("idx_portfolio_project_dependencies_successor", PortfolioProjectDependencyORM.successor_project_id)
