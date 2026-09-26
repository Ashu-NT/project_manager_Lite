from datetime import datetime, timezone

import pytest

from src.core.platform.application.integration import (
    InboxDeliveryDisposition,
    IntegrationInboxService,
)
from src.core.platform.contract.port.integration.accounting_outcomes import (
    AuthenticatedAccountingConnection,
    ExternalAccountingOutcome,
)
from src.core.platform.integration.accounting_events import (
    ACCOUNTING_OUTCOME_CONSUMER,
    accounting_outcome_envelope,
)
from src.tests.platform.integration.test_integration_delivery_foundation import (
    _Clock,
    delivery_store,  # noqa: F401
)


def _connection(**overrides):
    return AuthenticatedAccountingConnection(
        **{
            "tenant_id": "tenant-a",
            "organization_id": "org-a",
            "adapter_id": "adapter-a",
            "connection_id": "connection-a",
            "principal_name": "worker",
            "authoritative_sequence": True,
            **overrides,
        }
    )


def _outcome(**overrides):
    return ExternalAccountingOutcome(
        **{
            "schema_name": "external_accounting_outcome",
            "schema_version": 1,
            "external_event_id": "event-1",
            "tenant_id": "tenant-a",
            "organization_id": "org-a",
            "handoff_id": "handoff-a",
            "approved_source_version": 4,
            "handoff_payload_hash": "a" * 64,
            "outcome": "acknowledged",
            "sequence": 1,
            "occurred_at": datetime(2026, 9, 26, tzinfo=timezone.utc),
            **overrides,
        }
    )


def _service(request):
    session, _, _, repository = request.getfixturevalue("delivery_store")
    return (
        session,
        repository,
        IntegrationInboxService(
            repository=repository,
            consumer_name=ACCOUNTING_OUTCOME_CONSUMER,
            clock=_Clock(),
        ),
    )


def test_exact_replay_uses_existing_canonical_inbox(request):
    session, _, service = _service(request)
    envelope = accounting_outcome_envelope(_connection(), _outcome())
    decision = service.begin_delivery(envelope)
    assert decision.disposition is InboxDeliveryDisposition.READY
    service.mark_processed(decision.receipt.id)
    session.commit()
    replay = service.begin_delivery(envelope)
    assert replay.disposition is InboxDeliveryDisposition.DUPLICATE_PROCESSED
    assert replay.receipt.id == decision.receipt.id


@pytest.mark.parametrize(
    "overrides",
    [
        {"handoff_id": "handoff-b"},
        {"approved_source_version": 5},
        {"handoff_payload_hash": "b" * 64},
        {"outcome": "rejected"},
    ],
)
def test_same_event_changed_target_or_content_is_conflict(request, overrides):
    session, _, service = _service(request)
    original = accounting_outcome_envelope(_connection(), _outcome())
    decision = service.begin_delivery(original)
    service.mark_processed(decision.receipt.id)
    session.commit()
    changed = accounting_outcome_envelope(_connection(), _outcome(**overrides))
    assert changed.event_id == original.event_id
    conflict = service.begin_delivery(changed)
    assert conflict.disposition is InboxDeliveryDisposition.QUARANTINED
    assert conflict.receipt.envelope == original
    assert conflict.receipt.conflicting_envelope == changed


def test_unrelated_connectors_cannot_collide():
    first = accounting_outcome_envelope(_connection(), _outcome())
    second = accounting_outcome_envelope(
        _connection(connection_id="connection-b"), _outcome()
    )
    assert first.event_id != second.event_id
    assert first.aggregate_id != second.aggregate_id


@pytest.mark.parametrize("sequence", [1, 2])
def test_stale_or_equal_sequence_is_not_applied(request, sequence):
    session, _, service = _service(request)
    decision = service.begin_delivery(
        accounting_outcome_envelope(_connection(), _outcome(sequence=2))
    )
    service.mark_processed(decision.receipt.id)
    session.commit()
    rejected = service.begin_delivery(
        accounting_outcome_envelope(
            _connection(), _outcome(external_event_id="event-2", sequence=sequence)
        )
    )
    assert rejected.disposition is InboxDeliveryDisposition.QUARANTINED


def test_unsequenced_events_do_not_invent_handoff_revision(request):
    session, _, service = _service(request)
    connection = _connection(authoritative_sequence=False)
    first = accounting_outcome_envelope(connection, _outcome(sequence=None))
    second = accounting_outcome_envelope(
        connection,
        _outcome(
            external_event_id="event-2",
            sequence=None,
            outcome="reconciled",
            reconciliation_reference="reconciliation-1",
        ),
    )
    assert first.aggregate_id != second.aggregate_id
    assert first.payload["outcome"]["sequence"] is None
    decision = service.begin_delivery(first)
    service.mark_processed(decision.receipt.id)
    session.commit()
    assert service.begin_delivery(second).disposition is InboxDeliveryDisposition.READY


def test_rollback_does_not_leave_processed_receipt(request):
    session, repository, service = _service(request)
    decision = service.begin_delivery(
        accounting_outcome_envelope(_connection(), _outcome())
    )
    service.mark_processed(decision.receipt.id)
    session.rollback()
    assert repository.get(decision.receipt.id) is None
