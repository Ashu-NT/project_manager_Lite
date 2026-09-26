import pytest

from src.core.modules.project_management.domain.financials.accounting.outcome_policy import (
    OutcomeRejectionReason,
    validate_outcome_transition,
)
from src.core.platform.contract.port.integration.accounting_outcomes import (
    AccountingOutcomeKind,
)


@pytest.mark.parametrize(
    "previous,incoming,valid",
    [
        (None, AccountingOutcomeKind.ACKNOWLEDGED, True),
        (None, AccountingOutcomeKind.REJECTED, True),
        (None, AccountingOutcomeKind.RECONCILED, False),
        (AccountingOutcomeKind.ACKNOWLEDGED, AccountingOutcomeKind.RECONCILED, True),
        (AccountingOutcomeKind.ACKNOWLEDGED, AccountingOutcomeKind.REJECTED, False),
        (AccountingOutcomeKind.ACKNOWLEDGED, AccountingOutcomeKind.ACKNOWLEDGED, False),
        (AccountingOutcomeKind.RECONCILED, AccountingOutcomeKind.ACKNOWLEDGED, False),
        (AccountingOutcomeKind.REJECTED, AccountingOutcomeKind.ACKNOWLEDGED, False),
        (AccountingOutcomeKind.REJECTED, AccountingOutcomeKind.RECONCILED, False),
    ],
)
@pytest.mark.parametrize("sequenced", [False, True])
def test_monotonic_business_graph(previous, incoming, valid, sequenced):
    result = validate_outcome_transition(
        previous=previous,
        incoming=incoming,
        previous_sequence=1 if previous is not None and sequenced else None,
        incoming_sequence=2 if sequenced else None,
        authoritative_sequence=sequenced,
        transport_delivered=True,
    )
    assert result is (None if valid else OutcomeRejectionReason.INVALID_TRANSITION)


@pytest.mark.parametrize(
    "sequence,reason",
    [
        (1, OutcomeRejectionReason.STALE_SEQUENCE),
        (2, OutcomeRejectionReason.SEQUENCE_CONFLICT),
        (None, OutcomeRejectionReason.ORDERING_CONTRACT_MISMATCH),
    ],
)
def test_ordering_cannot_regress_state(sequence, reason):
    assert (
        validate_outcome_transition(
            previous=AccountingOutcomeKind.ACKNOWLEDGED,
            incoming=AccountingOutcomeKind.RECONCILED,
            previous_sequence=2,
            incoming_sequence=sequence,
            authoritative_sequence=True,
            transport_delivered=True,
        )
        is reason
    )


def test_business_acceptance_does_not_manufacture_transport_receipt():
    assert (
        validate_outcome_transition(
            previous=None,
            incoming=AccountingOutcomeKind.ACKNOWLEDGED,
            previous_sequence=None,
            incoming_sequence=None,
            authoritative_sequence=False,
            transport_delivered=False,
        )
        is OutcomeRejectionReason.TRANSPORT_NOT_DELIVERED
    )
