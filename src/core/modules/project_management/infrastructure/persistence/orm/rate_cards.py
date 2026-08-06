"""Canonical Project Finance rate-card rows."""

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
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.db.financial_numeric import (
    FinancialNumericKind,
    financial_numeric,
    financial_numeric_info,
)
from src.infra.persistence.orm.base import Base


class ProjectRateCardORM(Base):
    __tablename__ = "project_finance_rate_cards"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_rate_cards_scoped_organization",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_rate_cards_scoped_project",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "id",
            name="uq_pf_rate_cards_scoped_id",
        ),
        CheckConstraint("version >= 1", name="ck_pf_rate_cards_version"),
        CheckConstraint(
            "card_kind IS NULL OR card_kind = 'legacy'",
            name="ck_pf_rate_cards_card_kind",
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
    project_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    # 'legacy' marks the one auto-seeded, organization-wide card that holds
    # Resource.hourly_rate-derived fallback lines — NULL for every ordinary,
    # user-created card. The partial unique index below (one legacy card
    # per tenant/organization) is what makes get_or_create_legacy_card's
    # find-or-create race-safe at the database level, not just in-process.
    card_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("idx_pf_rate_cards_scope", ProjectRateCardORM.tenant_id, ProjectRateCardORM.organization_id)
Index("idx_pf_rate_cards_project", ProjectRateCardORM.project_id)
Index(
    "uq_pf_rate_cards_legacy_per_org",
    ProjectRateCardORM.tenant_id,
    ProjectRateCardORM.organization_id,
    unique=True,
    postgresql_where=(ProjectRateCardORM.card_kind == "legacy"),
    sqlite_where=(ProjectRateCardORM.card_kind == "legacy"),
)


class RateCardLineORM(Base):
    __tablename__ = "project_finance_rate_card_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "rate_card_id"],
            [
                "project_finance_rate_cards.tenant_id",
                "project_finance_rate_cards.organization_id",
                "project_finance_rate_cards.id",
            ],
            name="fk_pf_rate_card_lines_scoped_card",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "rate_type IN ('cost', 'billing')",
            name="ck_pf_rate_card_lines_rate_type",
        ),
        CheckConstraint(
            "origin IN ('configured', 'legacy_seeded')",
            name="ck_pf_rate_card_lines_origin",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_pf_rate_card_lines_effective_range",
        ),
        CheckConstraint(
            "(customer_party_id IS NULL AND contract_reference IS NULL) OR "
            "(customer_party_id IS NOT NULL AND contract_reference IS NOT NULL)",
            name="ck_pf_rate_card_lines_customer_contract",
        ),
        CheckConstraint(
            "NOT (resource_id IS NOT NULL AND "
            "(role IS NOT NULL OR skill_code IS NOT NULL OR department_id IS NOT NULL))",
            name="ck_pf_rate_card_lines_selection_key_exclusive",
        ),
        CheckConstraint(
            "resource_id IS NOT NULL OR role IS NOT NULL OR skill_code IS NOT NULL "
            "OR department_id IS NOT NULL",
            name="ck_pf_rate_card_lines_selection_key_required",
        ),
        CheckConstraint("rate_amount >= 0", name="ck_pf_rate_card_lines_rate_amount"),
        CheckConstraint("version >= 1", name="ck_pf_rate_card_lines_version"),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    rate_card_id: Mapped[str] = mapped_column(String, nullable=False)
    rate_type: Mapped[str] = mapped_column(String(16), nullable=False)
    origin: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default="configured"
    )
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    customer_party_id: Mapped[str | None] = mapped_column(String, nullable=True)
    contract_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    skill_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department_id: Mapped[str | None] = mapped_column(String, nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    rate_amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.RATE),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.RATE),
    )
    rate_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    overtime_multiplier: Mapped[Decimal | None] = mapped_column(
        financial_numeric(FinancialNumericKind.RATE),
        nullable=True,
        info=financial_numeric_info(FinancialNumericKind.RATE),
    )
    weekend_multiplier: Mapped[Decimal | None] = mapped_column(
        financial_numeric(FinancialNumericKind.RATE),
        nullable=True,
        info=financial_numeric_info(FinancialNumericKind.RATE),
    )
    holiday_multiplier: Mapped[Decimal | None] = mapped_column(
        financial_numeric(FinancialNumericKind.RATE),
        nullable=True,
        info=financial_numeric_info(FinancialNumericKind.RATE),
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_pf_rate_card_lines_scope",
    RateCardLineORM.tenant_id,
    RateCardLineORM.organization_id,
)
Index("idx_pf_rate_card_lines_card", RateCardLineORM.rate_card_id)
Index("idx_pf_rate_card_lines_resource", RateCardLineORM.resource_id)
Index(
    "idx_pf_rate_card_lines_role_skill_dept",
    RateCardLineORM.role,
    RateCardLineORM.skill_code,
    RateCardLineORM.department_id,
)


__all__ = ["ProjectRateCardORM", "RateCardLineORM"]
