from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base
from src.infra.persistence.orm.integration_delivery import IntegrationInboxORMMixin


class ProjectFinanceInboxORM(IntegrationInboxORMMixin, Base):
    __tablename__ = "project_finance_inbox_receipts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "source_project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pm_fin_inbox_scoped_source_project",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "source_resource_id"],
            ["resources.tenant_id", "resources.organization_id", "resources.id"],
            name="fk_pm_fin_inbox_scoped_source_resource",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "organization_id", "consumer_name", "event_id", name="uq_pm_fin_inbox_event"),
        UniqueConstraint("tenant_id", "organization_id", "deduplication_key", name="uq_pm_fin_inbox_dedupe"),
        CheckConstraint("status IN ('processing', 'retry', 'processed', 'quarantined', 'dead_letter')", name="ck_pm_fin_inbox_status"),
        CheckConstraint("aggregate_version >= 1 AND version >= 1", name="ck_pm_fin_inbox_versions"),
        CheckConstraint("attempt_count >= 1 AND max_attempts >= 1 AND attempt_count <= max_attempts", name="ck_pm_fin_inbox_attempts"),
        Index("idx_pm_fin_inbox_claim", "tenant_id", "organization_id", "status", "available_at", "occurred_at"),
        Index("idx_pm_fin_inbox_aggregate", "tenant_id", "organization_id", "consumer_name", "aggregate_type", "aggregate_id", "aggregate_version"),
        Index(
            "idx_pm_fin_inbox_approved_time_failures",
            "tenant_id",
            "organization_id",
            "source_project_id",
            "event_type",
            "status",
            "updated_at",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    source_project_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_work_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)


__all__ = ["ProjectFinanceInboxORM"]
