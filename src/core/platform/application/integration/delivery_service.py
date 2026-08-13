from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol
from uuid import uuid4

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.repositories.integration import (
    IntegrationInboxRepository,
    IntegrationOutboxRepository,
)
from src.core.platform.integration import (
    InboxProcessingStatus,
    IntegrationEventEnvelope,
    IntegrationInboxReceipt,
    IntegrationOutboxRecord,
    OutboxDeliveryStatus,
)


class DeliveryClock(Protocol):
    def now(self) -> datetime: ...


class InboxDeliveryDisposition(str, Enum):
    READY = "ready"
    DUPLICATE_PROCESSED = "duplicate_processed"
    ALREADY_PROCESSING = "already_processing"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class InboxDeliveryDecision:
    disposition: InboxDeliveryDisposition
    receipt: IntegrationInboxReceipt

    @property
    def should_apply(self) -> bool:
        return self.disposition == InboxDeliveryDisposition.READY


class IntegrationRetryPolicy:
    def __init__(
        self,
        *,
        initial_delay: timedelta = timedelta(seconds=5),
        maximum_delay: timedelta = timedelta(minutes=15),
    ) -> None:
        if initial_delay.total_seconds() <= 0 or maximum_delay < initial_delay:
            raise ValueError("Integration retry delays are invalid.")
        self._initial_delay = initial_delay
        self._maximum_delay = maximum_delay

    def next_attempt_at(self, *, now: datetime, attempt_count: int) -> datetime:
        multiplier = 2 ** max(0, attempt_count - 1)
        delay_seconds = min(
            self._initial_delay.total_seconds() * multiplier,
            self._maximum_delay.total_seconds(),
        )
        return now + timedelta(seconds=delay_seconds)


class IntegrationOutboxService:
    """Transaction-neutral source outbox lifecycle; callers own commit boundaries."""

    def __init__(
        self,
        *,
        repository: IntegrationOutboxRepository,
        owner_module: str,
        clock: DeliveryClock,
        retry_policy: IntegrationRetryPolicy | None = None,
        max_attempts: int = 8,
    ) -> None:
        self._repository = repository
        self._owner_module = str(owner_module or "").strip()
        self._clock = clock
        self._retry_policy = retry_policy or IntegrationRetryPolicy()
        self._max_attempts = max(1, int(max_attempts))

    def latest_for_aggregate(
        self, *, aggregate_type: str, aggregate_id: str
    ) -> IntegrationOutboxRecord | None:
        return self._repository.get_latest_by_aggregate(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
        )

    def enqueue(self, envelope: IntegrationEventEnvelope) -> IntegrationOutboxRecord:
        existing = self._repository.get_by_event_id(envelope.event_id)
        if existing is not None:
            if existing.envelope.envelope_hash == envelope.envelope_hash:
                return existing
            raise BusinessRuleError(
                "Integration event ID was reused with different immutable content.",
                code="INTEGRATION_OUTBOX_EVENT_ID_CONFLICT",
            )
        now = self._clock.now()
        record = IntegrationOutboxRecord(
            id=str(uuid4()),
            owner_module=self._owner_module,
            envelope=envelope,
            available_at=now,
            created_at=now,
            updated_at=now,
            max_attempts=self._max_attempts,
        )
        self._repository.add(record)
        self._repository.flush()
        return record

    def claim_batch(
        self, *, lease_token: str, lease_duration: timedelta, limit: int = 50
    ) -> list[IntegrationOutboxRecord]:
        now = self._clock.now()
        if lease_duration.total_seconds() <= 0:
            raise ValueError("Outbox lease duration must be positive.")
        return self._repository.claim_available(
            now=now,
            lease_token=str(lease_token or "").strip(),
            lease_expires_at=now + lease_duration,
            limit=max(1, min(int(limit), 200)),
        )

    def mark_published(
        self, record_id: str, *, lease_token: str
    ) -> IntegrationOutboxRecord:
        record = self._require_record(record_id)
        now = self._clock.now()
        record.require_lease(lease_token, at=now)
        candidate = replace(
            record,
            status=OutboxDeliveryStatus.PUBLISHED,
            lease_token=None,
            lease_expires_at=None,
            published_at=now,
            last_error_code=None,
            last_error_message=None,
            updated_at=now,
            row_version=record.row_version + 1,
        )
        self._repository.update(candidate, expected_row_version=record.row_version)
        return candidate

    def mark_failed(
        self,
        record_id: str,
        *,
        lease_token: str,
        error_code: str,
        error_message: str,
    ) -> IntegrationOutboxRecord:
        record = self._require_record(record_id)
        now = self._clock.now()
        record.require_lease(lease_token, at=now)
        dead = record.attempt_count >= record.max_attempts
        candidate = replace(
            record,
            status=(
                OutboxDeliveryStatus.DEAD_LETTER if dead else OutboxDeliveryStatus.RETRY
            ),
            available_at=(
                record.available_at
                if dead
                else self._retry_policy.next_attempt_at(
                    now=now, attempt_count=record.attempt_count
                )
            ),
            lease_token=None,
            lease_expires_at=None,
            last_error_code=str(error_code or "DELIVERY_FAILED").strip(),
            last_error_message=str(error_message or "Integration delivery failed.").strip(),
            updated_at=now,
            row_version=record.row_version + 1,
        )
        self._repository.update(candidate, expected_row_version=record.row_version)
        return candidate

    def _require_record(self, record_id: str) -> IntegrationOutboxRecord:
        record = self._repository.get(record_id)
        if record is None:
            raise BusinessRuleError(
                "Integration outbox record was not found in the active scope.",
                code="INTEGRATION_OUTBOX_NOT_FOUND",
            )
        return record


class IntegrationInboxService:
    """Consumer-owned inbox lifecycle; successful mutation and receipt share one transaction."""

    def __init__(
        self,
        *,
        repository: IntegrationInboxRepository,
        consumer_name: str,
        clock: DeliveryClock,
        retry_policy: IntegrationRetryPolicy | None = None,
        max_attempts: int = 8,
    ) -> None:
        self._repository = repository
        self._consumer_name = str(consumer_name or "").strip()
        self._clock = clock
        self._retry_policy = retry_policy or IntegrationRetryPolicy()
        self._max_attempts = max(1, int(max_attempts))

    def begin_delivery(
        self, envelope: IntegrationEventEnvelope
    ) -> InboxDeliveryDecision:
        key = envelope.inbox_deduplication_key(self._consumer_name)
        existing = self._repository.get_by_deduplication_key(key, for_update=True)
        now = self._clock.now()
        if existing is not None:
            if existing.envelope.envelope_hash != envelope.envelope_hash:
                quarantined = self._quarantine_candidate(
                    existing,
                    reason_code="EVENT_ID_CONTENT_CONFLICT",
                    now=now,
                    conflicting_envelope=envelope,
                )
                self._repository.update(
                    quarantined, expected_row_version=existing.row_version
                )
                return InboxDeliveryDecision(
                    InboxDeliveryDisposition.QUARANTINED, quarantined
                )
            if existing.status == InboxProcessingStatus.PROCESSED:
                return InboxDeliveryDecision(
                    InboxDeliveryDisposition.DUPLICATE_PROCESSED, existing
                )
            if existing.status in {
                InboxProcessingStatus.QUARANTINED,
                InboxProcessingStatus.DEAD_LETTER,
            }:
                return InboxDeliveryDecision(
                    InboxDeliveryDisposition.QUARANTINED, existing
                )
            if existing.status == InboxProcessingStatus.PROCESSING:
                return InboxDeliveryDecision(
                    InboxDeliveryDisposition.ALREADY_PROCESSING, existing
                )
            candidate = replace(
                existing,
                status=InboxProcessingStatus.PROCESSING,
                attempt_count=existing.attempt_count + 1,
                lease_token=None,
                lease_expires_at=None,
                last_error_code=None,
                last_error_message=None,
                updated_at=now,
                row_version=existing.row_version + 1,
            )
            self._repository.update(candidate, expected_row_version=existing.row_version)
            return InboxDeliveryDecision(InboxDeliveryDisposition.READY, candidate)

        latest_version = self._repository.latest_processed_aggregate_version(
            consumer_name=self._consumer_name,
            aggregate_type=envelope.aggregate_type,
            aggregate_id=envelope.aggregate_id,
        )
        status = InboxProcessingStatus.PROCESSING
        reason = None
        if latest_version is not None and envelope.aggregate_version <= latest_version:
            status = InboxProcessingStatus.QUARANTINED
            reason = "STALE_AGGREGATE_VERSION"
        receipt = IntegrationInboxReceipt(
            id=str(uuid4()),
            consumer_name=self._consumer_name,
            envelope=envelope,
            deduplication_key=key,
            status=status,
            quarantine_reason_code=reason,
            max_attempts=self._max_attempts,
            available_at=now,
            created_at=now,
            updated_at=now,
        )
        self._repository.add(receipt)
        self._repository.flush()
        return InboxDeliveryDecision(
            (
                InboxDeliveryDisposition.READY
                if status == InboxProcessingStatus.PROCESSING
                else InboxDeliveryDisposition.QUARANTINED
            ),
            receipt,
        )

    def mark_processed(self, receipt_id: str, *, lease_token: str | None = None) -> IntegrationInboxReceipt:
        receipt = self._require_receipt(receipt_id)
        if receipt.status != InboxProcessingStatus.PROCESSING:
            raise BusinessRuleError(
                "Only a processing inbox receipt can be completed.",
                code="INTEGRATION_INBOX_NOT_PROCESSING",
            )
        now = self._clock.now()
        self._require_inbox_lease(receipt, lease_token=lease_token, now=now)
        candidate = replace(
            receipt,
            status=InboxProcessingStatus.PROCESSED,
            processed_at=now,
            lease_token=None,
            lease_expires_at=None,
            last_error_code=None,
            last_error_message=None,
            updated_at=now,
            row_version=receipt.row_version + 1,
        )
        self._repository.update(candidate, expected_row_version=receipt.row_version)
        return candidate

    def record_failure(
        self, receipt_id: str, *, error_code: str, error_message: str, lease_token: str | None = None
    ) -> IntegrationInboxReceipt:
        receipt = self._require_receipt(receipt_id)
        now = self._clock.now()
        self._require_inbox_lease(receipt, lease_token=lease_token, now=now)
        dead = receipt.attempt_count >= receipt.max_attempts
        candidate = replace(
            receipt,
            status=(
                InboxProcessingStatus.DEAD_LETTER if dead else InboxProcessingStatus.RETRY
            ),
            available_at=(
                receipt.available_at
                if dead
                else self._retry_policy.next_attempt_at(
                    now=now, attempt_count=receipt.attempt_count
                )
            ),
            lease_token=None,
            lease_expires_at=None,
            last_error_code=str(error_code or "CONSUMER_FAILED").strip(),
            last_error_message=str(error_message or "Integration consumer failed.").strip(),
            updated_at=now,
            row_version=receipt.row_version + 1,
        )
        self._repository.update(candidate, expected_row_version=receipt.row_version)
        return candidate

    def quarantine(
        self, receipt_id: str, *, reason_code: str, message: str, lease_token: str | None = None
    ) -> IntegrationInboxReceipt:
        receipt = self._require_receipt(receipt_id)
        now = self._clock.now()
        self._require_inbox_lease(receipt, lease_token=lease_token, now=now)
        candidate = self._quarantine_candidate(receipt, reason_code=reason_code, now=now, message=message)
        self._repository.update(candidate, expected_row_version=receipt.row_version)
        return candidate

    @staticmethod
    def _quarantine_candidate(
        receipt: IntegrationInboxReceipt,
        *,
        reason_code: str,
        now: datetime,
        message: str = "Integration delivery was quarantined.",
        conflicting_envelope: IntegrationEventEnvelope | None = None,
    ) -> IntegrationInboxReceipt:
        return replace(
            receipt,
            status=InboxProcessingStatus.QUARANTINED,
            quarantine_reason_code=str(reason_code or "CONFLICT").strip(),
            lease_token=None,
            lease_expires_at=None,
            last_error_code=str(reason_code or "CONFLICT").strip(),
            last_error_message=str(message or "Integration delivery was quarantined.").strip(),
            conflicting_envelope=conflicting_envelope,
            conflict_detected_at=now if conflicting_envelope is not None else receipt.conflict_detected_at,
            updated_at=now,
            row_version=receipt.row_version + 1,
        )

    @staticmethod
    def _require_inbox_lease(
        receipt: IntegrationInboxReceipt, *, lease_token: str | None, now: datetime
    ) -> None:
        if receipt.lease_token is None:
            return
        if lease_token != receipt.lease_token or not receipt.lease_expires_at or receipt.lease_expires_at <= now:
            raise BusinessRuleError(
                "Inbox lease is missing, expired, or owned by another worker.",
                code="INTEGRATION_INBOX_LEASE_MISMATCH",
            )

    def _require_receipt(self, receipt_id: str) -> IntegrationInboxReceipt:
        receipt = self._repository.get(receipt_id)
        if receipt is None:
            raise BusinessRuleError(
                "Integration inbox receipt was not found in the active scope.",
                code="INTEGRATION_INBOX_NOT_FOUND",
            )
        return receipt


__all__ = [
    "InboxDeliveryDecision",
    "InboxDeliveryDisposition",
    "IntegrationInboxService",
    "IntegrationOutboxService",
    "IntegrationRetryPolicy",
]
