from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.infrastructure.persistence.orm.integration_outbox import ProcurementFinancialOutboxORM
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.integration_outbox import SqlAlchemyProcurementFinancialOutboxRepository
from src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox import ProjectFinanceInboxORM
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.finance_inbox import SqlAlchemyProjectFinanceInboxRepository
from src.core.platform.application.integration import (
    InboxDeliveryDisposition,
    IntegrationInboxService,
    IntegrationOutboxService,
    IntegrationRetryPolicy,
)
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.integration import IntegrationEventEnvelope, OutboxDeliveryStatus


class _Context:
    def __init__(self, tenant_id: str = "tenant-a", organization_id: str = "org-a") -> None:
        self.scope = ActiveScopeIds(tenant_id, organization_id)

    def require_active_scope_ids(self, *, operation_label: str) -> ActiveScopeIds:
        return self.scope


class _Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 9, 10, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


def _event(*, event_id: str = "event-1", version: int = 1, amount: str = "10") -> IntegrationEventEnvelope:
    return IntegrationEventEnvelope(
        event_id=event_id,
        event_type="procurement.purchase_order.commitment.changed.v1",
        schema_version=1,
        tenant_id="tenant-a",
        organization_id="org-a",
        aggregate_type="purchase_order",
        aggregate_id="po-1",
        aggregate_version=version,
        occurred_at=datetime(2026, 8, 9, 9, tzinfo=timezone.utc),
        payload={"amount": amount},
    )


@pytest.fixture
def delivery_store():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    ProcurementFinancialOutboxORM.__table__.create(engine)
    ProjectFinanceInboxORM.__table__.create(engine)
    with Session(engine) as session:
        context = _Context()
        outbox_repo = SqlAlchemyProcurementFinancialOutboxRepository(session)
        inbox_repo = SqlAlchemyProjectFinanceInboxRepository(session)
        outbox_repo._tenant_context_service = context
        inbox_repo._tenant_context_service = context
        yield session, context, outbox_repo, inbox_repo


def test_outbox_is_atomic_scoped_and_lease_owned(delivery_store) -> None:
    session, context, repo, _ = delivery_store
    clock = _Clock()
    service = IntegrationOutboxService(repository=repo, owner_module="inventory_procurement", clock=clock)

    created = service.enqueue(_event())
    assert created.status is OutboxDeliveryStatus.PENDING
    session.rollback()
    assert repo.get(created.id) is None

    created = service.enqueue(_event())
    session.commit()
    claimed = service.claim_batch(lease_token="worker-a", lease_duration=timedelta(seconds=30))
    assert claimed[0].attempt_count == 1
    with pytest.raises(BusinessRuleError, match="lease"):
        service.mark_published(created.id, lease_token="worker-b")
    published = service.mark_published(created.id, lease_token="worker-a")
    assert published.status is OutboxDeliveryStatus.PUBLISHED
    session.commit()

    context.scope = ActiveScopeIds("tenant-b", "org-b")
    assert repo.get(created.id) is None


def test_outbox_retries_then_dead_letters(delivery_store) -> None:
    session, _, repo, _ = delivery_store
    clock = _Clock()
    service = IntegrationOutboxService(
        repository=repo,
        owner_module="inventory_procurement",
        clock=clock,
        retry_policy=IntegrationRetryPolicy(initial_delay=timedelta(seconds=1), maximum_delay=timedelta(seconds=2)),
        max_attempts=2,
    )
    record = service.enqueue(_event())
    first = service.claim_batch(lease_token="worker", lease_duration=timedelta(seconds=10))[0]
    failed = service.mark_failed(first.id, lease_token="worker", error_code="BROKER_DOWN", error_message="offline")
    assert failed.status is OutboxDeliveryStatus.RETRY
    clock.advance(2)
    second = service.claim_batch(lease_token="worker", lease_duration=timedelta(seconds=10))[0]
    dead = service.mark_failed(second.id, lease_token="worker", error_code="BROKER_DOWN", error_message="offline")
    assert dead.status is OutboxDeliveryStatus.DEAD_LETTER
    session.commit()


def test_inbox_deduplicates_orders_and_quarantines_conflicts(delivery_store) -> None:
    session, _, _, repo = delivery_store
    clock = _Clock()
    service = IntegrationInboxService(repository=repo, consumer_name="project_finance", clock=clock)

    first = service.begin_delivery(_event())
    assert first.disposition is InboxDeliveryDisposition.READY
    service.mark_processed(first.receipt.id)
    session.commit()

    duplicate = service.begin_delivery(_event())
    assert duplicate.disposition is InboxDeliveryDisposition.DUPLICATE_PROCESSED

    conflict = service.begin_delivery(_event(amount="99"))
    assert conflict.disposition is InboxDeliveryDisposition.QUARANTINED
    assert conflict.receipt.quarantine_reason_code == "EVENT_ID_CONTENT_CONFLICT"
    assert conflict.receipt.conflicting_envelope is not None
    assert conflict.receipt.conflicting_envelope.payload["amount"] == "99"
    session.commit()

    stale = service.begin_delivery(_event(event_id="event-stale", version=1))
    assert stale.disposition is InboxDeliveryDisposition.QUARANTINED
    assert stale.receipt.quarantine_reason_code == "STALE_AGGREGATE_VERSION"


def test_delivery_migration_installs_owned_stores_and_envelope_guards(tmp_path) -> None:
    database_path = tmp_path / "integration-delivery.db"
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    inspector = sa.inspect(engine)
    assert {
        "platform_time_financial_outbox",
        "inventory_procurement_financial_outbox",
        "project_finance_inbox_receipts",
    }.issubset(inspector.get_table_names())
    with engine.connect() as connection:
        trigger_names = set(connection.execute(sa.text(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'trg_%_envelope_immutable'"
        )).scalars())
    assert trigger_names == {
        "trg_platform_time_financial_outbox_envelope_immutable",
        "trg_inventory_procurement_financial_outbox_envelope_immutable",
        "trg_project_finance_inbox_receipts_envelope_immutable",
    }
    engine.dispose()

    command.downgrade(config, "q4r5s6t7u8v9")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert "project_finance_inbox_receipts" not in sa.inspect(engine).get_table_names()
    engine.dispose()
