from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base
from src.infra.persistence.orm.integration_delivery import IntegrationOutboxORMMixin


class ProjectAccountingHandoffORM(Base):
    __tablename__ = "project_accounting_handoffs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "preparation_id"],
            [
                f"project_billing_preparations.{name}"
                for name in ("tenant_id", "organization_id", "project_id", "id")
            ],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "preparation_id",
            "approved_version",
            "handoff_kind",
            name="uq_pm_accounting_handoff_business",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "id",
            name="uq_pm_accounting_handoff_scope",
        ),
        CheckConstraint(
            "approved_version >= 1", name="ck_pm_accounting_approved_version"
        ),
        CheckConstraint(
            "handoff_kind = 'billing_preparation'", name="ck_pm_accounting_handoff_kind"
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    preparation_id: Mapped[str] = mapped_column(String, nullable=False)
    approved_version: Mapped[int] = mapped_column(Integer, nullable=False)
    handoff_kind: Mapped[str] = mapped_column(String, nullable=False)
    payload_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ProjectAccountingOutboxORM(IntegrationOutboxORMMixin, Base):
    __tablename__ = "project_accounting_outbox"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "event_id"],
            [
                f"project_accounting_handoffs.{name}"
                for name in ("tenant_id", "organization_id", "project_id", "id")
            ],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "event_id",
            name="uq_pm_accounting_outbox_event",
        ),
        CheckConstraint(
            "status IN ('pending', 'claimed', 'retry', 'published', 'dead_letter')",
            name="ck_pm_accounting_outbox_status",
        ),
        CheckConstraint(
            "aggregate_version >= 1 AND version >= 1",
            name="ck_pm_accounting_outbox_versions",
        ),
        CheckConstraint(
            "attempt_count >= 0 AND max_attempts >= 1 AND attempt_count <= max_attempts",
            name="ck_pm_accounting_outbox_attempts",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    target_adapter_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_connection_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_configuration_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transport_receipt_json: Mapped[str | None] = mapped_column(Text, nullable=True)
