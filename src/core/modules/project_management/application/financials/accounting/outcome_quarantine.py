"""Append-only-by-identity safe evidence using the existing PM-owned inbox store."""

from uuid import uuid4

from src.core.platform.application.integration.accounting.outcome_ingress import (
    ValidatedAccountingIngress,
)
from src.core.platform.contract.repositories.integration import (
    IntegrationInboxRepository,
)
from src.core.platform.integration import (
    InboxProcessingStatus,
    IntegrationEventEnvelope,
    IntegrationInboxReceipt,
)
from src.core.platform.integration.canonical_json import canonical_json_sha256

ACCOUNTING_QUARANTINE_CONSUMER = "project_management.accounting_quarantine.v1"


class AccountingOutcomeQuarantine:
    """Caller owns the authorized, serialized transaction and its commit.

    The inbox's conflict slot retains only the latest conflicting envelope. This
    separate consumer identity preserves EVERY distinct rejected body fingerprint
    instead of overwriting previous contradictory evidence. It stores no body,
    credential, provider message or externally claimed tenant/project identity.
    """

    def __init__(self, *, repository: IntegrationInboxRepository, clock):
        self._repository = repository
        self._clock = clock

    def record(
        self, ingress: ValidatedAccountingIngress, *, reason
    ) -> IntegrationInboxReceipt:
        # Reasons must be one of our finite enums, never arbitrary provider text.
        from src.core.modules.project_management.domain.financials.accounting.outcome_policy import (
            OutcomeRejectionReason,
        )
        from src.core.platform.application.integration.accounting.outcome_ingress import (
            IngressRejectionReason,
        )

        if not isinstance(reason, (IngressRejectionReason, OutcomeRejectionReason)):
            raise ValueError("A typed Accounting quarantine reason is required.")
        connection = ingress.connection
        payload = {
            "adapter_id": connection.adapter_id,
            "connection_id": connection.connection_id,
            "body_sha256": ingress.body_sha256,
            "byte_count": ingress.byte_count,
            "reason": reason.value,
        }
        identity = canonical_json_sha256(payload)
        now = self._clock.now()
        envelope = IntegrationEventEnvelope(
            event_id=identity,
            event_type="external_accounting.quarantine.v1",
            schema_version=1,
            tenant_id=connection.tenant_id,
            organization_id=connection.organization_id,
            aggregate_type="accounting_quarantine_evidence",
            aggregate_id=identity,
            aggregate_version=1,
            occurred_at=now,
            payload=payload,
        )
        key = envelope.inbox_deduplication_key(ACCOUNTING_QUARANTINE_CONSUMER)
        existing = self._repository.get_by_deduplication_key(key, for_update=True)
        if existing is not None:
            return existing
        receipt = IntegrationInboxReceipt(
            id=str(uuid4()),
            consumer_name=ACCOUNTING_QUARANTINE_CONSUMER,
            envelope=envelope,
            deduplication_key=key,
            status=InboxProcessingStatus.QUARANTINED,
            quarantine_reason_code=reason.value,
            last_error_code=reason.value,
            last_error_message="Accounting integration evidence was quarantined.",
            max_attempts=1,
            available_at=now,
            created_at=now,
            updated_at=now,
        )
        self._repository.add(receipt)
        self._repository.flush()
        return receipt
