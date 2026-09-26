"""Map authenticated external Accounting facts to the existing Platform inbox."""

from src.core.platform.contract.port.integration.accounting_outcomes import (
    AuthenticatedAccountingConnection,
    ExternalAccountingOutcome,
)
from src.core.platform.integration.canonical_json import canonical_json_sha256
from src.core.platform.integration.events import IntegrationEventEnvelope

ACCOUNTING_OUTCOME_CONSUMER = "project_management.accounting_outcomes.v1"
ACCOUNTING_OUTCOME_EVENT_TYPE = "external_accounting.outcome.v1"


def accounting_outcome_envelope(
    connection: AuthenticatedAccountingConnection,
    outcome: ExternalAccountingOutcome,
) -> IntegrationEventEnvelope:
    """Namespace event identity without including its mutable target/content.

    Including the handoff in event identity would let the same external event be
    replayed against another handoff unnoticed. Sequenced aggregates are handoffs;
    unsequenced aggregates are immutable events at version one, NOT a fabricated
    handoff sequence. The PM state machine governs unsequenced transitions.
    """
    if (outcome.tenant_id, outcome.organization_id) != (
        connection.tenant_id,
        connection.organization_id,
    ):
        raise ValueError("Authenticated Accounting scope mismatch.")
    if connection.authoritative_sequence != (outcome.sequence is not None):
        raise ValueError("Authenticated Accounting ordering contract mismatch.")
    source = {
        "tenant_id": connection.tenant_id,
        "organization_id": connection.organization_id,
        "adapter_id": connection.adapter_id,
        "connection_id": connection.connection_id,
    }
    event_id = canonical_json_sha256({**source, "event_id": outcome.external_event_id})
    return IntegrationEventEnvelope(
        event_id=event_id,
        event_type=ACCOUNTING_OUTCOME_EVENT_TYPE,
        schema_version=1,
        tenant_id=connection.tenant_id,
        organization_id=connection.organization_id,
        aggregate_type="accounting_handoff_outcome"
        if outcome.sequence is not None
        else "accounting_unsequenced_event",
        aggregate_id=canonical_json_sha256({**source, "handoff_id": outcome.handoff_id})
        if outcome.sequence is not None
        else event_id,
        aggregate_version=outcome.sequence if outcome.sequence is not None else 1,
        occurred_at=outcome.occurred_at,
        causation_id=outcome.handoff_id,
        payload={
            "adapter_id": connection.adapter_id,
            "connection_id": connection.connection_id,
            "outcome": outcome.model_dump(mode="json"),
        },
    )
