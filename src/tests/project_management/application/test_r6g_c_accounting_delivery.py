from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff import (
    ProjectAccountingOutboxORM,
)
from src.core.modules.project_management.infrastructure.persistence.uow.integration.accounting.accounting_delivery import (
    AccountingWorkerScope,
    SqlAlchemyAccountingDeliveryTransactions,
)
from src.core.platform.application.integration.accounting.delivery_processor import (
    ExternalAccountingDeliveryProcessor,
)
from src.core.platform.contract.port.integration.external_accounting import (
    ExternalAccountingDeliveryError,
    ExternalAccountingFailureKind,
    ExternalAccountingReceipt,
)
from src.infra.composition.integration.accounting.accounting_integration import (
    build_accounting_capability,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.tests.project_management.application.test_r6g_b_accounting_handoff import (
    approved_preparation,
)


@pytest.fixture
def worker(accounting_services, session):
    from src.core.modules.project_management.application.financials.invoicing.billing_events import (
        AccountingTransportFinalized,
    )
    from src.core.modules.project_management.application.financials.invoicing.event_handlers.view_invalidation import (
        build_billing_view_invalidation_handler,
    )

    approved = approved_preparation(accounting_services)
    accounting_services["billing_preparation_service"].request_delivery(
        approved.id, expected_row_version=approved.row_version
    )
    scope = accounting_services["tenant_context_service"].require_active_scope_ids(
        operation_label="test"
    )
    bus = InProcessPostCommitEventBus()
    bus.subscribe(AccountingTransportFinalized, build_billing_view_invalidation_handler(
        accounting_services["platform_view_invalidation_channel"],
    ))
    transactions = SqlAlchemyAccountingDeliveryTransactions(
        session_factory=sessionmaker(bind=session.bind, expire_on_commit=False),
        scope=AccountingWorkerScope(
            scope.tenant_id, scope.organization_id, approved.project_id
        ),
        authorize=lambda db, scope: (
            accounting_services["user_session"].principal.user_id
        ),
        capability_factory=lambda db, scope: build_accounting_capability(
            session=db,
            tenant_context_service=scope,
            user_session=scope,
            installed_adapters={"test_connector"},
        ),
        clock=SystemClock(),
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=bus,
    )
    adapter = Mock(supports_durable_idempotency=True)

    def deliver(*, evidence, target, credential):
        return ExternalAccountingReceipt(
            handoff_id=evidence.handoff_id,
            payload_hash=evidence.payload_hash,
            source_version=evidence.source_version,
            adapter_id=target.adapter_id,
            connection_id=target.connection_id,
            remote_reference="durable-test-reference",
            accepted_at=datetime.now(timezone.utc),
        )

    adapter.deliver.side_effect = deliver
    credentials = Mock()
    credentials.resolve.return_value = SecretStr("test-credential")
    processor = ExternalAccountingDeliveryProcessor(
        transactions=transactions,
        adapters={"test_connector": adapter},
        credentials=credentials,
    )
    return processor, transactions, adapter, approved


def test_transport_invalidation_is_post_commit_and_not_correlation_deduped(worker, accounting_services, session):
    from datetime import timedelta

    from sqlalchemy import update

    from src.tests.project_management.application.test_p39_finance_billing_full_modernization import (
        _spy_hints,
    )

    processor, transactions, _, approved = worker
    hints = _spy_hints(accounting_services)
    claim = transactions.claim()
    assert not hints
    transactions.finalize(claim, ExternalAccountingFailureKind.RETRYABLE)
    assert len(hints) == 1
    assert hints[0].scope_code == "billing_transport"
    assert hints[0].entity_id == approved.project_id
    session.execute(update(ProjectAccountingOutboxORM).values(available_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    session.commit()
    processor.process_one()
    assert len(hints) == 2
    assert all(hint.scope_code == "billing_transport" for hint in hints)


def test_durable_transport_receipt_does_not_acknowledge_business(
    worker, accounting_services, session
):
    processor, _, _, approved = worker
    session.rollback()
    assert processor.process_one()
    session.expire_all()
    row = session.scalars(select(ProjectAccountingOutboxORM)).one()
    assert row.status == "published"
    receipt = ExternalAccountingReceipt.model_validate_json(row.transport_receipt_json)
    assert receipt.handoff_id == row.event_id
    assert row.target_adapter_id == "test_connector"
    preparation = accounting_services["billing_preparation_service"].get_preparation(
        approved.id
    )
    assert preparation.status.value == "delivered"
    assert not processor.process_one()


@pytest.mark.parametrize(
    "kind,status",
    [
        (ExternalAccountingFailureKind.RETRYABLE, "retry"),
        (ExternalAccountingFailureKind.CONFIGURATION, "retry"),
        (ExternalAccountingFailureKind.CREDENTIAL, "retry"),
        (ExternalAccountingFailureKind.PERMANENT, "dead_letter"),
        (ExternalAccountingFailureKind.AMBIGUOUS, "dead_letter"),
    ],
)
def test_typed_transport_failure_preserves_approved_evidence(
    worker, accounting_services, session, kind, status
):
    processor, _, adapter, approved = worker
    adapter.deliver.side_effect = ExternalAccountingDeliveryError(kind)
    session.rollback()
    processor.process_one()
    session.expire_all()
    row = session.scalars(select(ProjectAccountingOutboxORM)).one()
    assert row.status == status and row.last_error_code == kind.value
    assert row.transport_receipt_json is None
    assert (
        accounting_services["billing_preparation_service"]
        .get_preparation(approved.id)
        .status.value
        == "delivery_pending"
    )
