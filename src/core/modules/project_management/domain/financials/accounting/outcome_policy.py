"""Accounting outcome causality is independent of transport and arrival timestamps."""

from enum import StrEnum

from src.core.platform.contract.port.integration.accounting_outcomes import (
    AccountingOutcomeKind,
)


class OutcomeRejectionReason(StrEnum):
    FOREIGN_HANDOFF = "foreign_handoff"
    CONNECTOR_MISMATCH = "connector_mismatch"
    SOURCE_MISMATCH = "source_mismatch"
    EVENT_CONTENT_CONFLICT = "event_content_conflict"
    ORDERING_CONTRACT_MISMATCH = "ordering_contract_mismatch"
    STALE_SEQUENCE = "stale_sequence"
    SEQUENCE_CONFLICT = "sequence_conflict"
    INVALID_TRANSITION = "invalid_transition"
    TRANSPORT_NOT_DELIVERED = "transport_not_delivered"


def validate_outcome_transition(
    *,
    previous: AccountingOutcomeKind | None,
    incoming: AccountingOutcomeKind,
    previous_sequence: int | None,
    incoming_sequence: int | None,
    authoritative_sequence: bool,
    transport_delivered: bool,
) -> OutcomeRejectionReason | None:
    """Return a finite quarantine reason; identical event replay is handled by inbox.

    Rejection is terminal for this handoff, not cancellation of PM approval. A
    correction gets its own handoff. Unsequenced sources use the same monotonic
    state graph, never synthetic ordering. Missing transport evidence is quarantined
    rather than being manufactured from an early business response.
    """
    if authoritative_sequence != (incoming_sequence is not None):
        return OutcomeRejectionReason.ORDERING_CONTRACT_MISMATCH
    if previous is not None and authoritative_sequence != (
        previous_sequence is not None
    ):
        return OutcomeRejectionReason.ORDERING_CONTRACT_MISMATCH
    if previous_sequence is not None and incoming_sequence is not None:
        if incoming_sequence < previous_sequence:
            return OutcomeRejectionReason.STALE_SEQUENCE
        if incoming_sequence == previous_sequence:
            return OutcomeRejectionReason.SEQUENCE_CONFLICT
    if not transport_delivered:
        return OutcomeRejectionReason.TRANSPORT_NOT_DELIVERED
    allowed = {
        None: {AccountingOutcomeKind.ACKNOWLEDGED, AccountingOutcomeKind.REJECTED},
        AccountingOutcomeKind.ACKNOWLEDGED: {AccountingOutcomeKind.RECONCILED},
        AccountingOutcomeKind.REJECTED: set(),
        AccountingOutcomeKind.RECONCILED: set(),
    }
    if incoming not in allowed[previous]:
        return OutcomeRejectionReason.INVALID_TRANSITION
    return None
