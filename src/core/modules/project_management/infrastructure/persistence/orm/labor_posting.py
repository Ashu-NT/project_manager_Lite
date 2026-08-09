from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.db.financial_numeric import FinancialNumericKind, financial_numeric, financial_numeric_info
from src.infra.persistence.orm.base import Base


class ApprovedTimeLaborPostingORM(Base):
    __tablename__ = "project_approved_time_labor_postings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_labor_postings_scoped_project", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "actual_cost_entry_id"],
            ["project_cost_entries.tenant_id", "project_cost_entries.organization_id", "project_cost_entries.project_id", "project_cost_entries.id"],
            name="fk_labor_postings_scoped_actual", ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "reversal_cost_entry_id"],
            ["project_cost_entries.tenant_id", "project_cost_entries.organization_id", "project_cost_entries.project_id", "project_cost_entries.id"],
            name="fk_labor_postings_scoped_reversal", ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "organization_id", "time_entry_id", "source_revision", name="uq_labor_postings_source_revision"),
        UniqueConstraint("tenant_id", "organization_id", "approved_snapshot_id", name="uq_labor_postings_snapshot"),
        CheckConstraint("source_revision >= 1 AND hours > 0 AND rate_amount >= 0", name="ck_labor_postings_values"),
        CheckConstraint("rate_card_version >= 1 AND rate_precedence_level >= 1", name="ck_labor_postings_rate_versions"),
        Index("idx_labor_postings_latest", "tenant_id", "organization_id", "time_entry_id", "source_revision"),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    time_entry_id: Mapped[str] = mapped_column(String, nullable=False)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    approved_snapshot_id: Mapped[str] = mapped_column(String, nullable=False)
    timesheet_period_id: Mapped[str] = mapped_column(String, nullable=False)
    actual_cost_entry_id: Mapped[str] = mapped_column(String, nullable=False)
    reversal_cost_entry_id: Mapped[str | None] = mapped_column(String, nullable=True)
    hours: Mapped[Decimal] = mapped_column(financial_numeric(FinancialNumericKind.QUANTITY), nullable=False, info=financial_numeric_info(FinancialNumericKind.QUANTITY))
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    rate_amount: Mapped[Decimal] = mapped_column(financial_numeric(FinancialNumericKind.RATE), nullable=False, info=financial_numeric_info(FinancialNumericKind.RATE))
    rate_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    rate_card_id: Mapped[str] = mapped_column(String, nullable=False)
    rate_line_id: Mapped[str] = mapped_column(String, nullable=False)
    rate_card_version: Mapped[int] = mapped_column(Integer, nullable=False)
    rate_precedence_level: Mapped[int] = mapped_column(Integer, nullable=False)
    rate_effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    rate_resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resource_id: Mapped[str] = mapped_column(String, nullable=False)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    employee_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


__all__ = ["ApprovedTimeLaborPostingORM"]
