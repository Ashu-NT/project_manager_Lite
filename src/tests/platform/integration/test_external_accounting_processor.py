from datetime import datetime, timezone
from hashlib import sha256
from threading import Event
from unittest.mock import Mock

import pytest
from pydantic import SecretStr, ValidationError

from src.application.runtime.accounting_delivery import run_accounting_delivery
from src.core.platform.application.integration.accounting.delivery_processor import (
    ExternalAccountingDeliveryProcessor,
)
from src.core.platform.contract.port.integration.external_accounting import (
    ExternalAccountingDeliveryError,
    ExternalAccountingEvidence,
    ExternalAccountingFailureKind,
    ExternalAccountingReceipt,
    ExternalAccountingTarget,
)
from src.core.platform.contract.uow.integration.accounting_delivery import (
    ClaimedAccountingDelivery,
)


@pytest.fixture
def delivery():
    evidence = ExternalAccountingEvidence(
        handoff_id="handoff",
        tenant_id="tenant",
        organization_id="org",
        project_id="project",
        source_id="preparation",
        source_version=2,
        schema_name="project_accounting_handoff.v1",
        schema_version=1,
        payload_bytes=b"{}",
        payload_hash=sha256(b"{}").hexdigest(),
    )
    target = ExternalAccountingTarget(
        tenant_id="tenant",
        organization_id="org",
        adapter_id="test",
        connection_id="connection",
        configuration_version=1,
    )
    claim = ClaimedAccountingDelivery(
        outbox_id="outbox",
        lease_token="lease",
        attempt_count=1,
        evidence=evidence,
        target=target,
        secret_reference="reference",
        preflight_failure=None,
    )
    receipt = ExternalAccountingReceipt(
        handoff_id="handoff",
        payload_hash=evidence.payload_hash,
        source_version=2,
        adapter_id="test",
        connection_id="connection",
        remote_reference="accepted",
        accepted_at=datetime.now(timezone.utc),
    )
    transactions = Mock()
    transactions.claim.return_value = claim
    adapter = Mock(supports_durable_idempotency=True)
    adapter.deliver.return_value = receipt
    credentials = Mock()
    credentials.resolve.return_value = SecretStr("never-log-this")
    processor = ExternalAccountingDeliveryProcessor(
        transactions=transactions, adapters={"test": adapter}, credentials=credentials
    )
    return processor, transactions, adapter, credentials, claim, receipt


def test_transport_only_receipt_and_detached_evidence(delivery):
    processor, transactions, adapter, _, claim, receipt = delivery
    assert processor.process_one()
    adapter.deliver.assert_called_once()
    assert adapter.deliver.call_args.kwargs["evidence"] is claim.evidence
    transactions.finalize.assert_called_once_with(claim, receipt)
    assert "never-log-this" not in repr(adapter.deliver.call_args)
    with pytest.raises(ValidationError):
        claim.evidence.handoff_id = "changed"


@pytest.mark.parametrize("kind", list(ExternalAccountingFailureKind))
def test_typed_failure_is_not_parsed_from_provider_text(delivery, kind):
    processor, transactions, adapter, _, claim, _ = delivery
    adapter.deliver.side_effect = ExternalAccountingDeliveryError(kind)
    assert processor.process_one()
    transactions.finalize.assert_called_once_with(claim, kind)


def test_unknown_provider_error_is_redacted_and_ambiguous(delivery, caplog):
    processor, transactions, adapter, _, claim, _ = delivery
    adapter.deliver.side_effect = RuntimeError("Authorization: never-log-this")
    processor.process_one()
    transactions.finalize.assert_called_once_with(
        claim, ExternalAccountingFailureKind.AMBIGUOUS
    )
    assert "never-log-this" not in caplog.text


def test_no_credential_or_unsupported_adapter_is_sent(delivery):
    processor, transactions, adapter, credentials, claim, _ = delivery
    adapter.supports_durable_idempotency = False
    processor.process_one()
    credentials.resolve.assert_not_called()
    adapter.deliver.assert_not_called()
    transactions.finalize.assert_called_once_with(
        claim, ExternalAccountingFailureKind.CONFIGURATION
    )


def test_secret_failure_is_safe(delivery, caplog):
    processor, transactions, adapter, credentials, claim, _ = delivery
    credentials.resolve.side_effect = RuntimeError("never-log-this")
    processor.process_one()
    adapter.deliver.assert_not_called()
    transactions.finalize.assert_called_once_with(
        claim, ExternalAccountingFailureKind.CREDENTIAL
    )
    assert "never-log-this" not in caplog.text


@pytest.mark.parametrize(
    "field,value",
    [
        ("handoff_id", "other"),
        ("payload_hash", "f" * 64),
        ("source_version", 3),
        ("adapter_id", "other"),
        ("connection_id", "other"),
    ],
)
def test_mismatched_receipt_cannot_finalize_as_delivered(delivery, field, value):
    processor, transactions, adapter, _, claim, receipt = delivery
    adapter.deliver.return_value = receipt.model_copy(update={field: value})
    processor.process_one()
    transactions.finalize.assert_called_once_with(
        claim, ExternalAccountingFailureKind.AMBIGUOUS
    )


def test_claim_commit_failure_never_calls_provider(delivery):
    processor, transactions, adapter, credentials, _, _ = delivery
    transactions.claim.side_effect = RuntimeError("database failed")
    with pytest.raises(RuntimeError):
        processor.process_one()
    credentials.resolve.assert_not_called()
    adapter.deliver.assert_not_called()


def test_finalize_failure_preserves_identity_for_idempotent_replay(delivery):
    processor, transactions, adapter, _, _, _ = delivery
    transactions.finalize.side_effect = [RuntimeError("commit failed"), None]
    with pytest.raises(RuntimeError):
        processor.process_one()
    processor.process_one()
    attempts = adapter.deliver.call_args_list
    assert attempts[0].kwargs["evidence"] == attempts[1].kwargs["evidence"]


def test_shutdown_before_claim_and_after_inflight_finalization(delivery):
    processor, transactions, adapter, _, _, receipt = delivery
    stop = Event()
    stop.set()
    run_accounting_delivery(processor, stop=stop)
    transactions.claim.assert_not_called()
    stop.clear()

    def finish_inflight(**kwargs):
        stop.set()
        return receipt

    adapter.deliver.side_effect = finish_inflight
    run_accounting_delivery(processor, stop=stop)
    transactions.claim.assert_called_once()
    transactions.finalize.assert_called_once()


def test_idle_runtime_waits_instead_of_spinning(delivery):
    processor, transactions, _, _, _, _ = delivery
    transactions.claim.return_value = None
    stop = Mock()
    stop.is_set.side_effect = [False, True]
    run_accounting_delivery(processor, stop=stop, idle_seconds=2)
    stop.wait.assert_called_once_with(2)


def test_unconfigured_executable_host_fails_before_database_access(monkeypatch):
    from src.application.runtime.accounting_delivery import main

    monkeypatch.delenv("PM_DB_URL", raising=False)
    assert main(["--tenant", "tenant", "--organization", "org", "--project", "project", "--principal", "worker"]) == 2


def test_executable_host_handles_termination_and_restores_signal_handlers(monkeypatch):
    import signal

    from src.application.runtime.accounting_delivery import main
    from src.infra.composition import accounting_delivery

    previous = signal.getsignal(signal.SIGTERM)
    processor = Mock()

    def completed_attempt():
        signal.raise_signal(signal.SIGTERM)
        return True

    processor.process_one.side_effect = completed_attempt
    monkeypatch.setattr(accounting_delivery, "build_external_accounting_processor", lambda **kwargs: processor)
    monkeypatch.setenv("PM_DB_URL", "sqlite:///:memory:")
    assert main(["--tenant", "tenant", "--organization", "org", "--project", "project", "--principal", "worker"],
                adapters={"test": Mock()}, credentials=Mock()) == 0
    processor.process_one.assert_called_once()
    assert signal.getsignal(signal.SIGTERM) == previous


def test_transport_contract_rejects_hash_tampering_and_legal_accounting_fields(delivery):
    _, _, _, _, claim, receipt = delivery
    with pytest.raises(ValidationError):
        ExternalAccountingEvidence.model_validate(claim.evidence.model_dump() | {"payload_bytes": b"tampered"})
    with pytest.raises(ValidationError):
        ExternalAccountingReceipt.model_validate(receipt.model_dump() | {"invoice_number": "not-transport-authority"})
    with pytest.raises(ValidationError):
        ExternalAccountingReceipt.model_validate(receipt.model_dump() | {"accepted_at": datetime(2026, 1, 1)})
