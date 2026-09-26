from dataclasses import replace
from hashlib import sha256

import pytest

from src.core.modules.project_management.application.financials.accounting.outcome_quarantine import (
    AccountingOutcomeQuarantine,
)
from src.core.platform.application.integration.accounting.outcome_ingress import (
    IngressRejectionReason,
    ValidatedAccountingIngress,
)
from src.core.platform.contract.port.integration.accounting_outcomes import (
    AuthenticatedAccountingConnection,
)
from src.tests.platform.integration.test_integration_delivery_foundation import (
    _Clock,
    delivery_store,  # noqa: F401
)


def _ingress(body=b'{"secret":"never-persist"'):
    return ValidatedAccountingIngress(
        connection=AuthenticatedAccountingConnection(
            tenant_id="tenant-a",
            organization_id="org-a",
            adapter_id="adapter-a",
            connection_id="connection-a",
            principal_name="worker",
            authoritative_sequence=True,
        ),
        body_sha256=sha256(body).hexdigest(),
        byte_count=len(body),
        outcome=None,
        rejection=IngressRejectionReason.MALFORMED,
    )


def test_repeated_bad_input_is_idempotent_without_overwriting_evidence(request):
    session, _, _, repository = request.getfixturevalue("delivery_store")
    clock = _Clock()
    service = AccountingOutcomeQuarantine(repository=repository, clock=clock)
    first = service.record(_ingress(), reason=IngressRejectionReason.MALFORMED)
    session.commit()
    clock.advance(5)
    repeated = service.record(_ingress(), reason=IngressRejectionReason.MALFORMED)
    assert repeated.id == first.id
    assert repeated.envelope == first.envelope
    assert repeated.row_version == first.row_version
    second = service.record(
        _ingress(b"another-conflict"), reason=IngressRejectionReason.MALFORMED
    )
    session.commit()
    assert second.id != first.id
    assert repository.get(first.id).envelope == first.envelope
    assert "never-persist" not in first.envelope.model_dump_json()
    assert set(first.envelope.payload) == {
        "adapter_id",
        "connection_id",
        "body_sha256",
        "byte_count",
        "reason",
    }


def test_quarantine_is_caller_transactional_and_scoped(request):
    session, context, _, repository = request.getfixturevalue("delivery_store")
    service = AccountingOutcomeQuarantine(repository=repository, clock=_Clock())
    receipt = service.record(_ingress(), reason=IngressRejectionReason.MALFORMED)
    session.rollback()
    assert repository.get(receipt.id) is None
    receipt = service.record(_ingress(), reason=IngressRejectionReason.MALFORMED)
    session.commit()
    context.scope = replace(context.scope, organization_id="org-b")
    assert repository.get(receipt.id) is None


def test_provider_error_text_cannot_be_a_reason(request):
    _, _, _, repository = request.getfixturevalue("delivery_store")
    service = AccountingOutcomeQuarantine(repository=repository, clock=_Clock())
    with pytest.raises(ValueError, match="typed"):
        service.record(_ingress(), reason="api-secret=private")
