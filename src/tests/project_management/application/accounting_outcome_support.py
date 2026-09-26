"""Test provider for exercising real delivery and authenticated outcome composition."""

import json
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

from pydantic import SecretBytes, SecretStr
from sqlalchemy import text

from src.core.modules.project_management.infrastructure.persistence.uow.integration.accounting.accounting_delivery import (
    AccountingWorkerScope,
)
from src.core.platform.contract.port.integration.accounting_outcomes import (
    AuthenticatedAccountingConnection,
)
from src.core.platform.contract.port.integration.external_accounting import (
    ExternalAccountingReceipt,
)
from src.infra.composition.integration.accounting.accounting_delivery import (
    build_external_accounting_processor,
)
from src.infra.composition.integration.accounting.accounting_outcomes import (
    build_external_accounting_ingress,
)


def outcome_sender(services, session):
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test ingress"
    )
    actor = str(uuid4())
    name = "inbound-" + actor
    now = datetime.now(timezone.utc)
    session.execute(
        text(
            "INSERT INTO users (id, username, password_hash, account_type, is_active, created_at, updated_at, version) VALUES (:id,:id,'no-login','service',true,:now,:now,1)"
        ),
        {"id": actor, "now": now.isoformat()},
    )
    session.execute(
        text(
            "INSERT INTO service_principals (id, tenant_id, organization_id, user_id, name, status, created_at, updated_at) VALUES (:id,:tenant,:org,:id,:name,'active',:now,:now)"
        ),
        {
            "id": actor,
            "tenant": scope.tenant_id,
            "org": scope.organization_id,
            "name": name,
            "now": now.isoformat(),
        },
    )
    session.commit()
    auth = Mock()
    auth.authenticate.return_value = AuthenticatedAccountingConnection(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        adapter_id="test_connector",
        connection_id="test_connection",
        principal_name=name,
        authoritative_sequence=True,
    )
    from src.core.modules.project_management.application.financials.invoicing.billing_events import (
        AccountingTransportFinalized,
        BillingPreparationExternalOutcomeRecorded,
    )
    from src.core.modules.project_management.application.financials.invoicing.event_handlers.view_invalidation import (
        build_billing_view_invalidation_handler,
    )
    from src.infra.events.in_process_post_commit_event_bus import (
        InProcessPostCommitEventBus,
    )

    bus = InProcessPostCommitEventBus()
    handler = build_billing_view_invalidation_handler(
        services["platform_view_invalidation_channel"]
    )
    bus.subscribe(BillingPreparationExternalOutcomeRecorded, handler)
    bus.subscribe(AccountingTransportFinalized, handler)
    ingress = build_external_accounting_ingress(
        engine=session.bind, authenticator=auth, post_commit_bus=bus
    )
    cached = {}

    def send(
        preparation_id,
        *,
        outcome,
        event_id=None,
        occurred_at=None,
        reconciliation_reference=None,
    ):
        preparation = services["billing_preparation_service"].get_preparation(
            preparation_id
        )
        if preparation.status.value == "delivery_pending":
            adapter = Mock(supports_durable_idempotency=True)
            adapter.deliver.side_effect = lambda *, evidence, target, credential: (
                ExternalAccountingReceipt(
                    handoff_id=evidence.handoff_id,
                    payload_hash=evidence.payload_hash,
                    source_version=evidence.source_version,
                    adapter_id=target.adapter_id,
                    connection_id=target.connection_id,
                    remote_reference="test-accepted",
                    accepted_at=now,
                )
            )
            credentials = Mock()
            credentials.resolve.return_value = SecretStr("test-only")
            processor = build_external_accounting_processor(
                engine=session.bind,
                scope=AccountingWorkerScope(
                    scope.tenant_id, scope.organization_id, preparation.project_id
                ),
                principal_name=name,
                adapters={"test_connector": adapter},
                credentials=credentials,
                post_commit_bus=bus,
            )
            session.commit()
            assert processor.process_one()
        row = session.execute(
            text(
                "SELECT id,approved_version,payload_hash FROM project_accounting_handoffs WHERE preparation_id=:id"
            ),
            {"id": preparation_id},
        ).one()
        key = event_id or str(uuid4())
        if key not in cached:
            cached[key] = dict(
                schema_name="external_accounting_outcome",
                schema_version=1,
                external_event_id=key,
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                handoff_id=row.id,
                approved_source_version=row.approved_version,
                handoff_payload_hash=row.payload_hash,
                outcome=outcome,
                sequence=2 if outcome == "reconciled" else 1,
                occurred_at=(occurred_at or now).isoformat(),
                reconciliation_reference=reconciliation_reference
                if outcome == "reconciled"
                else None,
            )
        session.commit()
        result = ingress.receive(
            body=json.dumps(cached[key]).encode(),
            authentication=SecretBytes(b"test-only"),
        )
        session.expire_all()
        return result

    return send
