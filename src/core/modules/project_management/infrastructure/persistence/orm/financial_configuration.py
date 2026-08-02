"""Canonical Project Finance configuration rows."""

from __future__ import annotations

from datetime import date, datetime

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
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class ProjectFinancialProfileORM(Base):
    __tablename__ = "project_finance_profiles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_profiles_scoped_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "default_cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_profiles_scoped_default_cost_code",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            name="uq_pf_profiles_scoped_project",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'on_hold', 'closed')",
            name="ck_pf_profiles_status",
        ),
        CheckConstraint(
            "billing_method IN ('non_billable', 'time_and_materials', 'fixed_price', 'cost_plus')",
            name="ck_pf_profiles_billing_method",
        ),
        CheckConstraint(
            "budget_control_mode IN ('none', 'warn', 'block')",
            name="ck_pf_profiles_budget_control_mode",
        ),
        CheckConstraint(
            "cost_code_policy IN ('all_active', 'restricted')",
            name="ck_pf_profiles_cost_code_policy",
        ),
        CheckConstraint(
            "financial_end_date IS NULL OR financial_start_date IS NULL OR "
            "financial_end_date >= financial_start_date",
            name="ck_pf_profiles_date_range",
        ),
        CheckConstraint(
            "(is_billable = false AND billing_method = 'non_billable') OR "
            "(is_billable = true AND billing_method <> 'non_billable')",
            name="ck_pf_profiles_billing_policy",
        ),
        CheckConstraint("version >= 1", name="ck_pf_profiles_version"),
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
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="active")
    billing_method: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="non_billable"
    )
    budget_control_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="warn"
    )
    cost_code_policy: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="all_active"
    )
    financial_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    financial_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_funded: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    is_billable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    default_cost_code_id: Mapped[str | None] = mapped_column(String, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("idx_pf_profiles_scope", ProjectFinancialProfileORM.tenant_id, ProjectFinancialProfileORM.organization_id)


class ProjectCostCodeORM(Base):
    __tablename__ = "project_finance_cost_codes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_cost_codes_scoped_organization",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "parent_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_cost_codes_scoped_parent",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "id",
            name="uq_pf_cost_codes_scoped_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "code",
            name="uq_pf_cost_codes_scoped_code",
        ),
        CheckConstraint(
            "length(code) >= 1 AND length(code) <= 64",
            name="ck_pf_cost_codes_code_length",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_pf_cost_codes_effective_range",
        ),
        CheckConstraint(
            "(external_system IS NULL AND external_reference IS NULL) OR "
            "(external_system IS NOT NULL AND external_reference IS NOT NULL)",
            name="ck_pf_cost_codes_external_mapping",
        ),
        CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="ck_pf_cost_codes_parent_not_self",
        ),
        CheckConstraint("version >= 1", name="ck_pf_cost_codes_version"),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(
        String, nullable=False, default="", server_default=""
    )
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    external_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("idx_pf_cost_codes_scope", ProjectCostCodeORM.tenant_id, ProjectCostCodeORM.organization_id)
Index("idx_pf_cost_codes_parent", ProjectCostCodeORM.parent_id)
Index("idx_pf_cost_codes_active", ProjectCostCodeORM.is_active)


class ProjectCostCodeRestrictionORM(Base):
    __tablename__ = "project_finance_cost_code_restrictions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_restrictions_scoped_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_restrictions_scoped_cost_code",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "cost_code_id",
            name="uq_pf_restrictions_project_cost_code",
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
    cost_code_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_pf_restrictions_project",
    ProjectCostCodeRestrictionORM.tenant_id,
    ProjectCostCodeRestrictionORM.organization_id,
    ProjectCostCodeRestrictionORM.project_id,
)


__all__ = [
    "ProjectCostCodeORM",
    "ProjectCostCodeRestrictionORM",
    "ProjectFinancialProfileORM",
]
