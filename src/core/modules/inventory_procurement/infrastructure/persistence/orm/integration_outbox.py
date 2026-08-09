from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from src.infra.persistence.orm.base import Base
from src.infra.persistence.orm.integration_delivery import IntegrationOutboxORMMixin


class ProcurementFinancialOutboxORM(IntegrationOutboxORMMixin, Base):
    __tablename__ = "inventory_procurement_financial_outbox"
    __table_args__ = (
        UniqueConstraint("tenant_id", "organization_id", "event_id", name="uq_proc_fin_outbox_event"),
        CheckConstraint("status IN ('pending', 'claimed', 'retry', 'published', 'dead_letter')", name="ck_proc_fin_outbox_status"),
        CheckConstraint("aggregate_version >= 1 AND version >= 1", name="ck_proc_fin_outbox_versions"),
        CheckConstraint("attempt_count >= 0 AND max_attempts >= 1 AND attempt_count <= max_attempts", name="ck_proc_fin_outbox_attempts"),
        Index("idx_proc_fin_outbox_claim", "tenant_id", "organization_id", "status", "available_at", "occurred_at"),
        {"info": {"rls_scope": "tenant_organization"}},
    )


__all__ = ["ProcurementFinancialOutboxORM"]
