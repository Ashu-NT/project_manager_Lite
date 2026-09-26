import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from pydantic import SecretBytes, ValidationError

from src.core.platform.application.integration.accounting.outcome_ingress import (
    MAX_ACCOUNTING_OUTCOME_BYTES,
    AccountingIngressAuthenticationError,
    AccountingIngressSizeError,
    AccountingOutcomeIngress,
    IngressRejectionReason,
)
from src.core.platform.contract.port.integration.accounting_outcomes import (
    AuthenticatedAccountingConnection,
    ExternalAccountingOutcome,
)


@pytest.fixture
def wire_outcome():
    return {
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
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def endpoint():
    auth = Mock()
    auth.authenticate.return_value = AuthenticatedAccountingConnection(
        tenant_id="tenant-a",
        organization_id="org-a",
        adapter_id="adapter-a",
        connection_id="connection-a",
        principal_name="inbound-worker",
        authoritative_sequence=True,
    )
    consumer = Mock()
    consumer.consume.side_effect = lambda ingress: ingress
    return (
        AccountingOutcomeIngress(authenticator=auth, consumer=consumer),
        auth,
        consumer,
    )


def test_authenticated_typed_outcome(endpoint, wire_outcome):
    ingress, auth, consumer = endpoint
    body = json.dumps(wire_outcome).encode()
    secret = SecretBytes(b"signature")
    result = ingress.receive(body=body, authentication=secret)
    auth.authenticate.assert_called_once_with(body=body, authentication=secret)
    consumer.consume.assert_called_once()
    assert result.outcome.handoff_id == "handoff-a"
    assert result.rejection is None
    assert result.byte_count == len(body)
    assert not hasattr(result, "body")
    assert "signature" not in repr(result)


@pytest.mark.parametrize("body", [b"{", b"not-json", b"null", b"[]", b"\xff"])
def test_malformed_authenticated_input_is_fingerprint_only(endpoint, body):
    ingress, _, _ = endpoint
    result = ingress.receive(body=body, authentication=SecretBytes(b"secret"))
    assert result.outcome is None
    assert result.rejection is IngressRejectionReason.MALFORMED
    assert len(result.body_sha256) == 64


def test_authentication_failure_never_reaches_consumer(endpoint):
    ingress, auth, consumer = endpoint
    auth.authenticate.side_effect = RuntimeError("secret=private-provider-response")
    with pytest.raises(AccountingIngressAuthenticationError) as error:
        ingress.receive(body=b"{}", authentication=SecretBytes(b"secret"))
    assert "private-provider" not in str(error.value)
    consumer.consume.assert_not_called()


def test_oversize_is_rejected_before_authentication_or_persistence(endpoint):
    ingress, auth, consumer = endpoint
    with pytest.raises(AccountingIngressSizeError):
        ingress.receive(
            body=b"x" * (MAX_ACCOUNTING_OUTCOME_BYTES + 1),
            authentication=SecretBytes(b"s"),
        )
    auth.authenticate.assert_not_called()
    consumer.consume.assert_not_called()


@pytest.mark.parametrize("field", ["tenant_id", "organization_id"])
def test_payload_cannot_authenticate_scope(endpoint, wire_outcome, field):
    ingress, _, _ = endpoint
    wire_outcome[field] = "foreign"
    result = ingress.receive(
        body=json.dumps(wire_outcome).encode(), authentication=SecretBytes(b"s")
    )
    assert result.rejection is IngressRejectionReason.SCOPE_MISMATCH
    assert result.connection.tenant_id == "tenant-a"
    assert result.connection.organization_id == "org-a"
    assert result.outcome is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 2),
        ("schema_version", True),
        ("approved_source_version", "4"),
        ("sequence", 0),
        ("sequence", True),
        ("project_id", "arbitrary-project"),
        ("preparation_id", "arbitrary-preparation"),
        ("invoice_amount", "100.00"),
        ("invoice_reference", "external-invoice"),
        ("payment_amount", "0"),
        ("external_status", "paid"),
        ("message", "<script>secret</script>"),
        ("outcome", "paid"),
        ("occurred_at", "2026-09-26T12:00:00"),
    ],
)
def test_invalid_or_unowned_fields_cannot_become_evidence(
    endpoint, wire_outcome, field, value
):
    ingress, _, _ = endpoint
    wire_outcome[field] = value
    result = ingress.receive(
        body=json.dumps(wire_outcome).encode(), authentication=SecretBytes(b"s")
    )
    assert result.outcome is None
    assert result.rejection is IngressRejectionReason.MALFORMED


def test_no_fabricated_sequence(endpoint, wire_outcome):
    ingress, auth, _ = endpoint
    wire_outcome["sequence"] = None
    result = ingress.receive(
        body=json.dumps(wire_outcome).encode(), authentication=SecretBytes(b"s")
    )
    assert result.rejection is IngressRejectionReason.ORDERING_MISMATCH
    auth.authenticate.return_value = auth.authenticate.return_value.model_copy(
        update={"authoritative_sequence": False}
    )
    result = ingress.receive(
        body=json.dumps(wire_outcome).encode(), authentication=SecretBytes(b"s")
    )
    assert result.rejection is None
    assert result.outcome.sequence is None


def test_reconciliation_requires_explicit_reference(wire_outcome):
    wire_outcome["outcome"] = "reconciled"
    with pytest.raises(ValidationError):
        ExternalAccountingOutcome.model_validate(wire_outcome)
    wire_outcome["reconciliation_reference"] = "reconciliation-1"
    outcome = ExternalAccountingOutcome.model_validate(wire_outcome)
    assert not hasattr(outcome, "payment_amount")
    assert not hasattr(outcome, "invoice_amount")


def test_duplicate_json_keys_are_quarantined(endpoint, wire_outcome):
    ingress, _, _ = endpoint
    body = json.dumps(wire_outcome).encode()
    body = body[:-1] + b', "handoff_id": "handoff-b"}'
    result = ingress.receive(body=body, authentication=SecretBytes(b"s"))
    assert result.rejection is IngressRejectionReason.MALFORMED
    assert result.outcome is None


@pytest.mark.parametrize("field", ["sequence", "approved_source_version"])
def test_revisions_fit_durable_integer_storage(wire_outcome, field):
    wire_outcome[field] = 2_147_483_648
    with pytest.raises(ValidationError):
        ExternalAccountingOutcome.model_validate(wire_outcome)


def test_equivalent_timestamp_offsets_normalize(wire_outcome):
    wire_outcome["occurred_at"] = "2026-09-26T12:00:00+02:00"
    first = ExternalAccountingOutcome.model_validate(wire_outcome)
    wire_outcome["occurred_at"] = "2026-09-26T10:00:00Z"
    second = ExternalAccountingOutcome.model_validate(wire_outcome)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
