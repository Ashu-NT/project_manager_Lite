"""PM-owned billing preparation and external accounting projection rows."""

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


_SCOPE_INFO = {"info": {"rls_scope": "tenant_organization"}}


class ProjectBillingProfileORM(Base):
    __tablename__ = "project_billing_profiles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_billing_profiles_scoped_organization",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_billing_profiles_scoped_project",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            name="uq_billing_profiles_project",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "id",
            name="uq_billing_profiles_scoped_id",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'on_hold', 'closed')",
            name="ck_billing_profiles_status",
        ),
        CheckConstraint("contract_value >= 0", name="ck_billing_profiles_contract_value"),
        CheckConstraint(
            "cost_plus_markup_percent >= 0 AND cost_plus_markup_percent <= 1000",
            name="ck_billing_profiles_markup",
        ),
        CheckConstraint(
            "payment_terms_days >= 0 AND payment_terms_days <= 3650",
            name="ck_billing_profiles_payment_terms",
        ),
        CheckConstraint(
            "retention_years >= 7 AND retention_years <= 100",
            name="ck_billing_profiles_retention",
        ),
        CheckConstraint("version >= 1", name="ck_billing_profiles_version"),
        CheckConstraint(
            "external_customer_reference IS NULL OR customer_party_id IS NOT NULL",
            name="ck_billing_profiles_external_customer_party",
        ),
        _SCOPE_INFO,
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    contract_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    contract_value: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    customer_party_id: Mapped[str | None] = mapped_column(String, nullable=True)
    external_customer_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    purchase_order_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cost_plus_markup_percent: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.PERCENTAGE),
        nullable=False,
        default=Decimal("0"),
        info=financial_numeric_info(FinancialNumericKind.PERCENTAGE),
    )
    payment_terms_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    retention_years: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_billing_profiles_scope",
    ProjectBillingProfileORM.tenant_id,
    ProjectBillingProfileORM.organization_id,
)


class ProjectBillingScheduleLineORM(Base):
    __tablename__ = "project_billing_schedule_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "billing_profile_id"],
            [
                "project_billing_profiles.tenant_id",
                "project_billing_profiles.organization_id",
                "project_billing_profiles.project_id",
                "project_billing_profiles.id",
            ],
            name="fk_billing_schedule_scoped_profile",
            ondelete="CASCADE",
        ),
        CheckConstraint("amount > 0", name="ck_billing_schedule_amount"),
        CheckConstraint(
            "status IN ('planned', 'ready', 'billed', 'cancelled')",
            name="ck_billing_schedule_status",
        ),
        CheckConstraint("version >= 1", name="ck_billing_schedule_version"),
        _SCOPE_INFO,
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    billing_profile_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    task_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=True
    )
    acceptance_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_billing_schedule_project",
    ProjectBillingScheduleLineORM.tenant_id,
    ProjectBillingScheduleLineORM.organization_id,
    ProjectBillingScheduleLineORM.project_id,
)
Index("idx_billing_schedule_due", ProjectBillingScheduleLineORM.due_date)


class ProjectBillingPreparationORM(Base):
    __tablename__ = "project_billing_preparations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "billing_profile_id"],
            [
                "project_billing_profiles.tenant_id",
                "project_billing_profiles.organization_id",
                "project_billing_profiles.project_id",
                "project_billing_profiles.id",
            ],
            name="fk_billing_preparations_scoped_profile",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "correction_of_preparation_id"],
            [
                "project_billing_preparations.tenant_id",
                "project_billing_preparations.organization_id",
                "project_billing_preparations.project_id",
                "project_billing_preparations.id",
            ],
            name="fk_billing_preparations_scoped_correction",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "preparation_number",
            name="uq_billing_preparations_number",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "idempotency_key",
            name="uq_billing_preparations_idempotency",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "id",
            name="uq_billing_preparations_scoped_id",
        ),
        CheckConstraint(
            "billing_method IN ('time_and_materials', 'fixed_price', 'cost_plus')",
            name="ck_billing_preparations_method",
        ),
        CheckConstraint("period_end >= period_start", name="ck_billing_preparations_period"),
        CheckConstraint("line_count >= 0", name="ck_billing_preparations_line_count"),
        CheckConstraint(
            "total_amount >= 0 OR correction_of_preparation_id IS NOT NULL",
            name="ck_billing_preparations_negative_correction",
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'delivery_pending', "
            "'delivered', 'acknowledged', 'reconciled', 'rejected', 'cancelled')",
            name="ck_billing_preparations_status",
        ),
        CheckConstraint("version >= 1", name="ck_billing_preparations_version"),
        _SCOPE_INFO,
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    billing_profile_id: Mapped[str] = mapped_column(String, nullable=False)
    preparation_number: Mapped[str] = mapped_column(String(64), nullable=False)
    billing_method: Mapped[str] = mapped_column(String(32), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        default=Decimal("0"),
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    correction_of_preparation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    approval_request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_notes: Mapped[str] = mapped_column(String, nullable=False, default="")
    delivery_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_billing_preparations_project",
    ProjectBillingPreparationORM.tenant_id,
    ProjectBillingPreparationORM.organization_id,
    ProjectBillingPreparationORM.project_id,
)
Index("idx_billing_preparations_status", ProjectBillingPreparationORM.status)


class ProjectBillingPreparationLineORM(Base):
    __tablename__ = "project_billing_preparation_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "preparation_id"],
            [
                "project_billing_preparations.tenant_id",
                "project_billing_preparations.organization_id",
                "project_billing_preparations.project_id",
                "project_billing_preparations.id",
            ],
            name="fk_billing_lines_scoped_preparation",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "source_type IN ('approved_time', 'posted_cost', 'schedule_line', 'adjustment')",
            name="ck_billing_lines_source_type",
        ),
        CheckConstraint("quantity <> 0", name="ck_billing_lines_quantity"),
        CheckConstraint("net_amount <> 0", name="ck_billing_lines_net_amount"),
        CheckConstraint(
            "(rate_card_id IS NULL AND rate_line_id IS NULL AND rate_card_version IS NULL) OR "
            "(rate_card_id IS NOT NULL AND rate_line_id IS NOT NULL AND rate_card_version >= 1)",
            name="ck_billing_lines_rate_snapshot",
        ),
        _SCOPE_INFO,
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    preparation_id: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    source_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.QUANTITY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.QUANTITY),
    )
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    unit_rate: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.RATE),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.RATE),
    )
    net_amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_amount: Mapped[Decimal | None] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=True,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    markup_percent: Mapped[Decimal | None] = mapped_column(
        financial_numeric(FinancialNumericKind.PERCENTAGE),
        nullable=True,
        info=financial_numeric_info(FinancialNumericKind.PERCENTAGE),
    )
    rate_card_id: Mapped[str | None] = mapped_column(String, nullable=True)
    rate_line_id: Mapped[str | None] = mapped_column(String, nullable=True)
    rate_card_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("idx_billing_lines_preparation", ProjectBillingPreparationLineORM.preparation_id)
Index(
    "idx_billing_lines_source",
    ProjectBillingPreparationLineORM.tenant_id,
    ProjectBillingPreparationLineORM.organization_id,
    ProjectBillingPreparationLineORM.source_type,
    ProjectBillingPreparationLineORM.source_id,
)


class ProjectBillingSourceLockORM(Base):
    __tablename__ = "project_billing_source_locks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "preparation_id"],
            [
                "project_billing_preparations.tenant_id",
                "project_billing_preparations.organization_id",
                "project_billing_preparations.project_id",
                "project_billing_preparations.id",
            ],
            name="fk_billing_locks_scoped_preparation",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["preparation_line_id"],
            ["project_billing_preparation_lines.id"],
            name="fk_billing_locks_line",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "source_type",
            "source_id",
            name="uq_billing_locks_source",
        ),
        CheckConstraint(
            "status IN ('reserved', 'finalized', 'released')",
            name="ck_billing_locks_status",
        ),
        _SCOPE_INFO,
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    preparation_id: Mapped[str] = mapped_column(String, nullable=False)
    preparation_line_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index(
    "idx_billing_locks_preparation",
    ProjectBillingSourceLockORM.tenant_id,
    ProjectBillingSourceLockORM.organization_id,
    ProjectBillingSourceLockORM.preparation_id,
)


class ProjectBillingExternalEventORM(Base):
    __tablename__ = "project_billing_external_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "preparation_id"],
            [
                "project_billing_preparations.tenant_id",
                "project_billing_preparations.organization_id",
                "project_billing_preparations.project_id",
                "project_billing_preparations.id",
            ],
            name="fk_billing_events_scoped_preparation",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "external_system",
            "idempotency_key",
            name="uq_billing_events_idempotency",
        ),
        CheckConstraint(
            "event_type IN ('delivery_accepted', 'delivery_rejected', "
            "'status_updated', 'reconciled')",
            name="ck_billing_events_type",
        ),
        CheckConstraint(
            "event_type <> 'reconciled' OR reconciliation_reference IS NOT NULL",
            name="ck_billing_events_reconciliation",
        ),
        _SCOPE_INFO,
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    preparation_id: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)
    external_system: Mapped[str] = mapped_column(String(80), nullable=False)
    external_status: Mapped[str] = mapped_column(String(80), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    external_invoice_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reconciliation_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    message: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_billing_events_preparation",
    ProjectBillingExternalEventORM.tenant_id,
    ProjectBillingExternalEventORM.organization_id,
    ProjectBillingExternalEventORM.preparation_id,
    ProjectBillingExternalEventORM.occurred_at,
)


__all__ = [
    "ProjectBillingExternalEventORM",
    "ProjectBillingPreparationLineORM",
    "ProjectBillingPreparationORM",
    "ProjectBillingProfileORM",
    "ProjectBillingScheduleLineORM",
    "ProjectBillingSourceLockORM",
]
