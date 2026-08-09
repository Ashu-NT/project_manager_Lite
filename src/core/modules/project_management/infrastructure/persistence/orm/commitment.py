"""Canonical PM commitment projections and immutable actual matches."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.db.financial_numeric import (
    FinancialNumericKind,
    financial_numeric,
    financial_numeric_info,
)
from src.infra.persistence.orm.base import Base


class ProjectCommitmentORM(Base):
    __tablename__ = "project_commitments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_project_commitments_scoped_project",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_project_commitments_scoped_project_id",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "purchase_order_id",
            name="uq_project_commitments_source_po",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    purchase_order_id: Mapped[str] = mapped_column(String(128), nullable=False)
    purchase_order_number: Mapped[str] = mapped_column(String(128), nullable=False)
    supplier_party_id: Mapped[str] = mapped_column(
        String, ForeignKey("parties.id", ondelete="RESTRICT"), nullable=False
    )
    site_id: Mapped[str] = mapped_column(
        String, ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectCommitmentLineORM(Base):
    __tablename__ = "project_commitment_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_project_commitment_lines_scoped_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "commitment_id"],
            [
                "project_commitments.tenant_id",
                "project_commitments.organization_id",
                "project_commitments.project_id",
                "project_commitments.id",
            ],
            name="fk_project_commitment_lines_scoped_header",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_project_commitment_lines_scoped_cost_code",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            name="fk_project_commitment_lines_project_task",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_project_commitment_lines_scoped_project_id",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "commitment_id", "purchase_order_line_id",
            name="uq_project_commitment_lines_source_line",
        ),
        CheckConstraint(
            "state IN ('sent', 'partially_received', 'fully_received', 'closed', 'cancelled')",
            name="ck_project_commitment_lines_state",
        ),
        CheckConstraint("ordered_quantity > 0", name="ck_project_commitment_lines_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_project_commitment_lines_rate"),
        CheckConstraint(
            "amount >= 0 AND base_amount >= 0 AND matched_amount >= 0 "
            "AND matched_amount <= amount",
            name="ck_project_commitment_lines_amounts",
        ),
        CheckConstraint("exchange_rate > 0", name="ck_project_commitment_lines_fx"),
        CheckConstraint(
            "source_revision >= 1 AND version >= 1",
            name="ck_project_commitment_lines_versions",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    commitment_id: Mapped[str] = mapped_column(String, nullable=False)
    purchase_order_line_id: Mapped[str] = mapped_column(String(128), nullable=False)
    cost_code_id: Mapped[str] = mapped_column(String, nullable=False)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    ordered_quantity: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.QUANTITY), nullable=False,
        info=financial_numeric_info(FinancialNumericKind.QUANTITY),
    )
    quantity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.RATE), nullable=False,
        info=financial_numeric_info(FinancialNumericKind.RATE),
    )
    amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY), nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    base_amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY), nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    base_currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.EXCHANGE_RATE), nullable=False,
        info=financial_numeric_info(FinancialNumericKind.EXCHANGE_RATE),
    )
    exchange_rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    exchange_rate_source: Mapped[str] = mapped_column(String(128), nullable=False)
    exchange_rate_captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    matched_amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY), nullable=False, default=0, server_default="0",
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    order_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_requisition_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_requisition_line_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectCommitmentSourceRevisionORM(Base):
    __tablename__ = "project_commitment_source_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "commitment_line_id"],
            [
                "project_commitment_lines.tenant_id",
                "project_commitment_lines.organization_id",
                "project_commitment_lines.project_id",
                "project_commitment_lines.id",
            ],
            name="fk_project_commitment_revisions_scoped_line",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "commitment_line_id", "source_revision",
            name="uq_project_commitment_revisions_line_revision",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "source_idempotency_key",
            name="uq_project_commitment_revisions_idempotency",
        ),
        CheckConstraint("source_revision >= 1", name="ck_project_commitment_revisions_version"),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    commitment_line_id: Mapped[str] = mapped_column(String, nullable=False)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectCommitmentMatchORM(Base):
    __tablename__ = "project_commitment_matches"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "commitment_line_id"],
            [
                "project_commitment_lines.tenant_id",
                "project_commitment_lines.organization_id",
                "project_commitment_lines.project_id",
                "project_commitment_lines.id",
            ],
            name="fk_project_commitment_matches_scoped_line",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "cost_entry_id"],
            [
                "project_cost_entries.tenant_id",
                "project_cost_entries.organization_id",
                "project_cost_entries.project_id",
                "project_cost_entries.id",
            ],
            name="fk_project_commitment_matches_scoped_cost_entry",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "reverses_match_id"],
            [
                "project_commitment_matches.tenant_id",
                "project_commitment_matches.organization_id",
                "project_commitment_matches.project_id",
                "project_commitment_matches.id",
            ],
            name="fk_project_commitment_matches_scoped_reversal",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_project_commitment_matches_scoped_project_id",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "idempotency_key",
            name="uq_project_commitment_matches_idempotency",
        ),
        CheckConstraint("kind IN ('match', 'reversal')", name="ck_project_commitment_matches_kind"),
        CheckConstraint(
            "(kind = 'match' AND amount > 0 AND reverses_match_id IS NULL) OR "
            "(kind = 'reversal' AND amount < 0 AND reverses_match_id IS NOT NULL)",
            name="ck_project_commitment_matches_sign",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    commitment_line_id: Mapped[str] = mapped_column(String, nullable=False)
    cost_entry_id: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY), nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    reverses_match_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_project_commitments_scope_project",
    ProjectCommitmentORM.tenant_id, ProjectCommitmentORM.organization_id, ProjectCommitmentORM.project_id,
)
Index(
    "idx_project_commitment_lines_project_state",
    ProjectCommitmentLineORM.tenant_id, ProjectCommitmentLineORM.organization_id,
    ProjectCommitmentLineORM.project_id, ProjectCommitmentLineORM.state,
)
Index(
    "idx_project_commitment_matches_line",
    ProjectCommitmentMatchORM.tenant_id, ProjectCommitmentMatchORM.organization_id,
    ProjectCommitmentMatchORM.commitment_line_id, ProjectCommitmentMatchORM.created_at,
)
Index(
    "uq_project_commitment_matches_original_actual",
    ProjectCommitmentMatchORM.tenant_id, ProjectCommitmentMatchORM.organization_id,
    ProjectCommitmentMatchORM.cost_entry_id,
    unique=True,
    postgresql_where=ProjectCommitmentMatchORM.kind == "match",
    sqlite_where=ProjectCommitmentMatchORM.kind == "match",
)
Index(
    "uq_project_commitment_matches_one_reversal",
    ProjectCommitmentMatchORM.tenant_id, ProjectCommitmentMatchORM.organization_id,
    ProjectCommitmentMatchORM.reverses_match_id,
    unique=True,
    postgresql_where=ProjectCommitmentMatchORM.reverses_match_id.is_not(None),
    sqlite_where=ProjectCommitmentMatchORM.reverses_match_id.is_not(None),
)


__all__ = [
    "ProjectCommitmentLineORM",
    "ProjectCommitmentMatchORM",
    "ProjectCommitmentORM",
    "ProjectCommitmentSourceRevisionORM",
]
