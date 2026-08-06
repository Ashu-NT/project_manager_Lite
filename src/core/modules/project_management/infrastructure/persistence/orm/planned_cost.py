"""Canonical Project Finance planned-cost snapshot rows."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.db.financial_numeric import (
    FinancialNumericKind,
    financial_numeric,
    financial_numeric_info,
)
from src.infra.persistence.orm.base import Base


class ProjectPlannedCostVersionORM(Base):
    __tablename__ = "project_finance_planned_cost_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_planned_cost_versions_scoped_organization",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_planned_cost_versions_scoped_project",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "id",
            name="uq_pf_planned_cost_versions_scoped_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "id",
            name="uq_pf_planned_cost_versions_scope_project_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "revision",
            name="uq_pf_planned_cost_versions_project_revision",
        ),
        CheckConstraint(
            "status IN ('current', 'superseded')",
            name="ck_pf_planned_cost_versions_status",
        ),
        CheckConstraint("revision >= 1", name="ck_pf_planned_cost_versions_revision"),
        CheckConstraint("version >= 1", name="ck_pf_planned_cost_versions_version"),
        CheckConstraint(
            "unresolved_rate_count >= 0",
            name="ck_pf_planned_cost_versions_unresolved_rate_count",
        ),
        CheckConstraint(
            "partially_allocated_resource_count >= 0",
            name="ck_pf_planned_cost_versions_partial_alloc_count",
        ),
        CheckConstraint(
            "unclassified_line_count >= 0",
            name="ck_pf_planned_cost_versions_unclassified_count",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="current", server_default="current"
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    calculated_by: Mapped[str] = mapped_column(String, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Completeness has three independent meanings — see
    # ProjectPlannedCostVersion's docstring in domain/financials/planned_cost.py.
    rates_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    allocations_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    cost_codes_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    unresolved_rate_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    partially_allocated_resource_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    unclassified_line_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    superseded_by: Mapped[str | None] = mapped_column(String, nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Plain optimistic-concurrency token (domain field `row_version`) — same
    # "version" ↔ "row_version" translation `budget.py`'s mapper already uses.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_pf_planned_cost_versions_scope",
    ProjectPlannedCostVersionORM.tenant_id,
    ProjectPlannedCostVersionORM.organization_id,
)
Index("idx_pf_planned_cost_versions_project", ProjectPlannedCostVersionORM.project_id)
Index(
    # At most one CURRENT version per project at any time.
    "uq_pf_planned_cost_versions_one_current_per_project",
    ProjectPlannedCostVersionORM.tenant_id,
    ProjectPlannedCostVersionORM.organization_id,
    ProjectPlannedCostVersionORM.project_id,
    unique=True,
    postgresql_where=(ProjectPlannedCostVersionORM.status == "current"),
    sqlite_where=(ProjectPlannedCostVersionORM.status == "current"),
)


class ProjectPlannedCostLineORM(Base):
    __tablename__ = "project_finance_planned_cost_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "version_id"],
            [
                "project_finance_planned_cost_versions.tenant_id",
                "project_finance_planned_cost_versions.organization_id",
                "project_finance_planned_cost_versions.project_id",
                "project_finance_planned_cost_versions.id",
            ],
            name="fk_pf_planned_cost_lines_scoped_version",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_planned_cost_lines_scoped_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_planned_cost_lines_scoped_cost_code",
            ondelete="RESTRICT",
        ),
        CheckConstraint("planned_hours >= 0", name="ck_pf_planned_cost_lines_hours"),
        CheckConstraint("rate_amount >= 0", name="ck_pf_planned_cost_lines_rate_amount"),
        CheckConstraint("amount >= 0", name="ck_pf_planned_cost_lines_amount"),
        CheckConstraint(
            "rate_card_version >= 1", name="ck_pf_planned_cost_lines_rate_card_version"
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    version_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    # RESTRICT: a task/resource referenced by any snapshot line (current or
    # superseded) is a structural dimension of that line, not mere
    # provenance — deleting it must not silently corrupt persisted history.
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resource_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("resources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_resource_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("project_resources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cost_code_id: Mapped[str] = mapped_column(String, nullable=False)
    # Plain, immutable, snapshotted identifier — deliberately NOT a live
    # foreign key. The line's hours/rate/amount/currency/dimensions are
    # already fully self-contained, so deleting the operational
    # TaskAssignment later (a routine scheduling action) must not be
    # blocked, and must not erase which record produced this line's
    # numbers (see ProjectPlannedCostLine's docstring).
    source_assignment_id: Mapped[str] = mapped_column(String, nullable=False)
    planned_hours: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.QUANTITY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.QUANTITY),
    )
    rate_amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.RATE),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.RATE),
    )
    amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    rate_card_id: Mapped[str] = mapped_column(String, nullable=False)
    rate_line_id: Mapped[str] = mapped_column(String, nullable=False)
    rate_card_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_pf_planned_cost_lines_scope",
    ProjectPlannedCostLineORM.tenant_id,
    ProjectPlannedCostLineORM.organization_id,
)
Index("idx_pf_planned_cost_lines_version", ProjectPlannedCostLineORM.version_id)
Index("idx_pf_planned_cost_lines_task", ProjectPlannedCostLineORM.task_id)
Index("idx_pf_planned_cost_lines_cost_code", ProjectPlannedCostLineORM.cost_code_id)


__all__ = ["ProjectPlannedCostLineORM", "ProjectPlannedCostVersionORM"]
