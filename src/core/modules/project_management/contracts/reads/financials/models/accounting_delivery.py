"""Immutable external delivery projection; no credentials or worker dependencies."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AccountingDeliveryFact:
    handoff_id: str
    approved_source_version: int
    requested_at: datetime
    transport_state: str
    adapter_id: str | None
    connection_id: str | None
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime | None
    delivered_at: datetime | None
    last_activity_at: datetime
    failure_category: str | None
    receipt_reference: str | None
    quarantined_count: int = 0
    latest_quarantine_id: str | None = None
    latest_quarantine_at: datetime | None = None
    latest_quarantine_reason: str | None = None
    external_sequence: int | None = None


__all__ = ["AccountingDeliveryFact"]
