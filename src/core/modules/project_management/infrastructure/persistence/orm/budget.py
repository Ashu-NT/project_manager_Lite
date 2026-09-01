"""Canonical Project Finance budget rows."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
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


class ProjectBudgetORM(Base):
    __tablename__ = "project_finance_budgets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_budgets_scoped_organization",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_budgets_scoped_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "predecessor_budget_id"],
            [
                "project_finance_budgets.tenant_id",
                "project_finance_budgets.organization_id",
                "project_finance_budgets.project_id",
                "project_finance_budgets.id",
            ],
            name="fk_pf_budgets_scoped_predecessor",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "id",
            name="uq_pf_budgets_scoped_id",
        ),
        # Enables the line's four-column composite FK below, which is what
        # actually guarantees BudgetLine.project_id == ProjectBudget.project_id
        # at the database level (not just as a service-level convention).
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "id",
            name="uq_pf_budget_scope_project_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "revision",
            name="uq_pf_budget_project_revision",
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'rejected', 'superseded', 'closed')",
            name="ck_pf_budgets_status",
        ),
        CheckConstraint("revision >= 1", name="ck_pf_budgets_revision"),
        CheckConstraint("version >= 1", name="ck_pf_budgets_version"),
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
    predecessor_budget_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )
    # Business version within the project (v1, v2, v3...) — assigned once,
    # never changes on this row. Distinct from `version` below, which is
    # the plain optimistic-concurrency token `update_with_version_check`
    # expects on a column literally named `version` (mapped to the domain
    # field `row_version` — see mappers/budget.py).
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    submitted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(String, nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    submission_notes: Mapped[str] = mapped_column(
        String, nullable=False, default="", server_default=""
    )
    approval_notes: Mapped[str] = mapped_column(
        String, nullable=False, default="", server_default=""
    )
    rejection_notes: Mapped[str] = mapped_column(
        String, nullable=False, default="", server_default=""
    )
    closure_notes: Mapped[str] = mapped_column(
        String, nullable=False, default="", server_default=""
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("idx_pf_budgets_scope", ProjectBudgetORM.tenant_id, ProjectBudgetORM.organization_id)
Index("idx_pf_budgets_project", ProjectBudgetORM.project_id)
Index(
    # At most one APPROVED budget per project at any time.
    "uq_pf_budgets_one_approved_per_project",
    ProjectBudgetORM.tenant_id,
    ProjectBudgetORM.organization_id,
    ProjectBudgetORM.project_id,
    unique=True,
    postgresql_where=(ProjectBudgetORM.status == "approved"),
    sqlite_where=(ProjectBudgetORM.status == "approved"),
)
Index(
    # At most one open (draft/submitted) iteration per project at any time.
    # A rejected version does not block the next draft; an approved
    # version may coexist with one draft/submitted successor.
    "uq_pf_budgets_one_open_per_project",
    ProjectBudgetORM.tenant_id,
    ProjectBudgetORM.organization_id,
    ProjectBudgetORM.project_id,
    unique=True,
    postgresql_where=ProjectBudgetORM.status.in_(["draft", "submitted"]),
    sqlite_where=ProjectBudgetORM.status.in_(["draft", "submitted"]),
)


class BudgetLineORM(Base):
    __tablename__ = "project_finance_budget_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "budget_id"],
            [
                "project_finance_budgets.tenant_id",
                "project_finance_budgets.organization_id",
                "project_finance_budgets.project_id",
                "project_finance_budgets.id",
            ],
            name="fk_pf_budget_lines_scoped_budget",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_budget_lines_scoped_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_budget_lines_scoped_cost_code",
            ondelete="RESTRICT",
        ),
        CheckConstraint("amount >= 0", name="ck_pf_budget_lines_amount"),
        CheckConstraint("version >= 1", name="ck_pf_budget_lines_version"),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    budget_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    cost_code_id: Mapped[str] = mapped_column(String, nullable=False)
    # RESTRICT, not SET NULL: a task referenced by any budget line — even
    # one belonging to a REJECTED/DRAFT budget — must not be silently
    # detached by deleting the task. SET NULL would let an already-
    # APPROVED, supposedly-immutable line lose its WBS dimension with no
    # BudgetService call, no row_version bump, and no audit trail.
    task_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="RESTRICT"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_pf_budget_lines_scope",
    BudgetLineORM.tenant_id,
    BudgetLineORM.organization_id,
)
Index("idx_pf_budget_lines_budget", BudgetLineORM.budget_id)
Index("idx_pf_budget_lines_cost_code", BudgetLineORM.cost_code_id)
Index("idx_pf_budget_lines_task", BudgetLineORM.task_id)


__all__ = ["BudgetLineORM", "ProjectBudgetORM"]
