from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from src.infra.persistence.orm.base import Base
from src.infra.persistence.orm.integration_delivery import IntegrationInboxORMMixin


class ProjectFinanceInboxORM(IntegrationInboxORMMixin, Base):
    __tablename__ = "project_finance_inbox_receipts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "organization_id", "consumer_name", "event_id", name="uq_pm_fin_inbox_event"),
        UniqueConstraint("tenant_id", "organization_id", "deduplication_key", name="uq_pm_fin_inbox_dedupe"),
        CheckConstraint("status IN ('processing', 'retry', 'processed', 'quarantined', 'dead_letter')", name="ck_pm_fin_inbox_status"),
        CheckConstraint("aggregate_version >= 1 AND version >= 1", name="ck_pm_fin_inbox_versions"),
        CheckConstraint("attempt_count >= 1 AND max_attempts >= 1 AND attempt_count <= max_attempts", name="ck_pm_fin_inbox_attempts"),
        Index("idx_pm_fin_inbox_claim", "tenant_id", "organization_id", "status", "available_at", "occurred_at"),
        Index("idx_pm_fin_inbox_aggregate", "tenant_id", "organization_id", "consumer_name", "aggregate_type", "aggregate_id", "aggregate_version"),
        {"info": {"rls_scope": "tenant_organization"}},
    )


__all__ = ["ProjectFinanceInboxORM"]
