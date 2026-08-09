from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import TenantScopedRepositorySupport
from src.core.platform.integration import (
    InboxProcessingStatus,
    IntegrationEventEnvelope,
    IntegrationInboxReceipt,
    IntegrationOutboxRecord,
    OutboxDeliveryStatus,
)
from src.infra.persistence.db.optimistic import update_with_version_check


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _envelope(row: Any) -> IntegrationEventEnvelope:
    envelope = IntegrationEventEnvelope.model_validate_json(row.envelope_json)
    if envelope.envelope_hash != row.envelope_hash:
        raise BusinessRuleError(
            "Persisted integration envelope failed its integrity check.",
            code="INTEGRATION_ENVELOPE_INTEGRITY_FAILED",
        )
    return envelope


class SqlAlchemyIntegrationOutboxRepository(TenantScopedRepositorySupport):
    _repository_label = "Integration outbox repository"

    def __init__(self, session: Session, *, orm_type: type[Any], owner_module: str) -> None:
        self.session = session
        self._orm_type = orm_type
        self._owner_module = owner_module
        self._tenant_context_service = None

    def add(self, record: IntegrationOutboxRecord) -> None:
        ctx = self._context(operation_label="enqueue integration event")
        self._require_scope(record, ctx)
        if record.owner_module != self._owner_module:
            raise BusinessRuleError("Outbox owner does not match the owned store.", code="INTEGRATION_OUTBOX_OWNER_MISMATCH")
        envelope = record.envelope
        self.session.add(self._orm_type(
            id=record.id, tenant_id=record.tenant_id, organization_id=record.organization_id,
            event_id=envelope.event_id, event_type=envelope.event_type,
            aggregate_type=envelope.aggregate_type, aggregate_id=envelope.aggregate_id,
            aggregate_version=envelope.aggregate_version, occurred_at=envelope.occurred_at,
            envelope_json=envelope.model_dump_json(), envelope_hash=envelope.envelope_hash,
            status=record.status.value, attempt_count=record.attempt_count,
            max_attempts=record.max_attempts, available_at=record.available_at,
            lease_token=record.lease_token, lease_expires_at=record.lease_expires_at,
            published_at=record.published_at, last_error_code=record.last_error_code,
            last_error_message=record.last_error_message, created_at=record.created_at,
            updated_at=record.updated_at, version=record.row_version,
        ))

    def get(self, record_id: str) -> IntegrationOutboxRecord | None:
        row = self._get_in_scope(self._orm_type, record_id, operation_label="access integration outbox")
        return self._from_row(row) if row else None

    def get_by_event_id(self, event_id: str) -> IntegrationOutboxRecord | None:
        ctx = self._context(operation_label="access integration event")
        row = self.session.execute(select(self._orm_type).where(
            self._orm_type.tenant_id == ctx.tenant_id,
            self._orm_type.organization_id == ctx.organization_id,
            self._orm_type.event_id == event_id,
        )).scalar_one_or_none()
        return self._from_row(row) if row else None

    def get_latest_by_aggregate(
        self, *, aggregate_type: str, aggregate_id: str
    ) -> IntegrationOutboxRecord | None:
        ctx = self._context(operation_label="access integration aggregate history")
        row = self.session.execute(
            select(self._orm_type).where(
                self._orm_type.tenant_id == ctx.tenant_id,
                self._orm_type.organization_id == ctx.organization_id,
                self._orm_type.aggregate_type == aggregate_type,
                self._orm_type.aggregate_id == aggregate_id,
            ).order_by(self._orm_type.aggregate_version.desc()).limit(1)
        ).scalar_one_or_none()
        return self._from_row(row) if row else None

    def claim_available(self, *, now: datetime, lease_token: str, lease_expires_at: datetime, limit: int) -> list[IntegrationOutboxRecord]:
        if not lease_token:
            raise ValueError("Outbox lease token is required.")
        ctx = self._context(operation_label="claim integration outbox")
        eligible = or_(
            (self._orm_type.status.in_([OutboxDeliveryStatus.PENDING.value, OutboxDeliveryStatus.RETRY.value])) & (self._orm_type.available_at <= now),
            (self._orm_type.status == OutboxDeliveryStatus.CLAIMED.value) & (self._orm_type.lease_expires_at <= now),
        )
        rows = self.session.execute(
            select(self._orm_type).where(
                self._orm_type.tenant_id == ctx.tenant_id,
                self._orm_type.organization_id == ctx.organization_id,
                eligible,
            ).order_by(self._orm_type.aggregate_type, self._orm_type.aggregate_id, self._orm_type.aggregate_version, self._orm_type.occurred_at, self._orm_type.id)
            .limit(limit).with_for_update(skip_locked=True)
        ).scalars().all()
        for row in rows:
            row.status = OutboxDeliveryStatus.CLAIMED.value
            row.attempt_count += 1
            row.lease_token = lease_token
            row.lease_expires_at = lease_expires_at
            row.updated_at = now
            row.version += 1
        self.session.flush()
        return [self._from_row(row) for row in rows]

    def update(self, record: IntegrationOutboxRecord, *, expected_row_version: int) -> None:
        ctx = self._context(operation_label="update integration outbox")
        self._require_scope(record, ctx)
        update_with_version_check(self.session, self._orm_type, record.id, expected_row_version, {
            "status": record.status.value, "attempt_count": record.attempt_count,
            "max_attempts": record.max_attempts, "available_at": record.available_at,
            "lease_token": record.lease_token, "lease_expires_at": record.lease_expires_at,
            "published_at": record.published_at, "last_error_code": record.last_error_code,
            "last_error_message": record.last_error_message, "updated_at": record.updated_at,
        }, not_found_message="Integration outbox record not found.", stale_message="Integration outbox record was changed concurrently.", extra_filters={"tenant_id": ctx.tenant_id, "organization_id": ctx.organization_id})

    def flush(self) -> None:
        self.session.flush()

    @staticmethod
    def _require_scope(record: IntegrationOutboxRecord, ctx: Any) -> None:
        if record.tenant_id != ctx.tenant_id or record.organization_id != ctx.organization_id:
            raise BusinessRuleError("Integration event is outside the active scope.", code="INTEGRATION_SCOPE_VIOLATION")

    def _from_row(self, row: Any) -> IntegrationOutboxRecord:
        return IntegrationOutboxRecord(
            id=row.id, owner_module=self._owner_module, envelope=_envelope(row),
            status=row.status, attempt_count=row.attempt_count, max_attempts=row.max_attempts,
            available_at=_aware(row.available_at), lease_token=row.lease_token,
            lease_expires_at=_aware(row.lease_expires_at), published_at=_aware(row.published_at),
            last_error_code=row.last_error_code, last_error_message=row.last_error_message,
            created_at=_aware(row.created_at), updated_at=_aware(row.updated_at), row_version=row.version,
        )


class SqlAlchemyIntegrationInboxRepository(TenantScopedRepositorySupport):
    _repository_label = "Integration inbox repository"

    def __init__(self, session: Session, *, orm_type: type[Any]) -> None:
        self.session = session
        self._orm_type = orm_type
        self._tenant_context_service = None

    def add(self, receipt: IntegrationInboxReceipt) -> None:
        ctx = self._context(operation_label="record integration delivery")
        self._require_scope(receipt, ctx)
        envelope = receipt.envelope
        self.session.add(self._orm_type(
            id=receipt.id, tenant_id=receipt.tenant_id, organization_id=receipt.organization_id,
            event_id=envelope.event_id, event_type=envelope.event_type,
            aggregate_type=envelope.aggregate_type, aggregate_id=envelope.aggregate_id,
            aggregate_version=envelope.aggregate_version, occurred_at=envelope.occurred_at,
            envelope_json=envelope.model_dump_json(), envelope_hash=envelope.envelope_hash,
            consumer_name=receipt.consumer_name, deduplication_key=receipt.deduplication_key,
            status=receipt.status.value, attempt_count=receipt.attempt_count,
            max_attempts=receipt.max_attempts, available_at=receipt.available_at,
            lease_token=receipt.lease_token, lease_expires_at=receipt.lease_expires_at,
            processed_at=receipt.processed_at, quarantine_reason_code=receipt.quarantine_reason_code,
            conflicting_envelope_json=(receipt.conflicting_envelope.model_dump_json() if receipt.conflicting_envelope else None),
            conflicting_envelope_hash=(receipt.conflicting_envelope.envelope_hash if receipt.conflicting_envelope else None),
            conflict_detected_at=receipt.conflict_detected_at,
            last_error_code=receipt.last_error_code, last_error_message=receipt.last_error_message,
            created_at=receipt.created_at, updated_at=receipt.updated_at, version=receipt.row_version,
        ))

    def get(self, receipt_id: str) -> IntegrationInboxReceipt | None:
        row = self._get_in_scope(self._orm_type, receipt_id, operation_label="access integration inbox")
        return self._from_row(row) if row else None

    def get_by_deduplication_key(self, deduplication_key: str, *, for_update: bool = False) -> IntegrationInboxReceipt | None:
        ctx = self._context(operation_label="deduplicate integration delivery")
        stmt = select(self._orm_type).where(
            self._orm_type.tenant_id == ctx.tenant_id,
            self._orm_type.organization_id == ctx.organization_id,
            self._orm_type.deduplication_key == deduplication_key,
        )
        if for_update:
            stmt = stmt.with_for_update()
        row = self.session.execute(stmt).scalar_one_or_none()
        return self._from_row(row) if row else None

    def latest_processed_aggregate_version(self, *, consumer_name: str, aggregate_type: str, aggregate_id: str) -> int | None:
        ctx = self._context(operation_label="check integration event ordering")
        return self.session.execute(select(func.max(self._orm_type.aggregate_version)).where(
            self._orm_type.tenant_id == ctx.tenant_id,
            self._orm_type.organization_id == ctx.organization_id,
            self._orm_type.consumer_name == consumer_name,
            self._orm_type.aggregate_type == aggregate_type,
            self._orm_type.aggregate_id == aggregate_id,
            self._orm_type.processed_at.is_not(None),
        )).scalar_one()

    def claim_available(self, *, now: datetime, lease_token: str, lease_expires_at: datetime, limit: int) -> list[IntegrationInboxReceipt]:
        if not lease_token:
            raise ValueError("Inbox lease token is required.")
        ctx = self._context(operation_label="claim integration inbox")
        eligible = or_(
            (self._orm_type.status == InboxProcessingStatus.RETRY.value) & (self._orm_type.available_at <= now),
            (self._orm_type.status == InboxProcessingStatus.PROCESSING.value) & (self._orm_type.lease_token.is_not(None)) & (self._orm_type.lease_expires_at <= now),
        )
        rows = self.session.execute(select(self._orm_type).where(
            self._orm_type.tenant_id == ctx.tenant_id,
            self._orm_type.organization_id == ctx.organization_id,
            eligible,
        ).order_by(self._orm_type.aggregate_type, self._orm_type.aggregate_id, self._orm_type.aggregate_version, self._orm_type.occurred_at, self._orm_type.id).limit(limit).with_for_update(skip_locked=True)).scalars().all()
        for row in rows:
            row.status = InboxProcessingStatus.PROCESSING.value
            row.attempt_count += 1
            row.lease_token = lease_token
            row.lease_expires_at = lease_expires_at
            row.updated_at = now
            row.version += 1
        self.session.flush()
        return [self._from_row(row) for row in rows]

    def update(self, receipt: IntegrationInboxReceipt, *, expected_row_version: int) -> None:
        ctx = self._context(operation_label="update integration inbox")
        self._require_scope(receipt, ctx)
        update_with_version_check(self.session, self._orm_type, receipt.id, expected_row_version, {
            "status": receipt.status.value, "attempt_count": receipt.attempt_count,
            "max_attempts": receipt.max_attempts, "available_at": receipt.available_at,
            "lease_token": receipt.lease_token, "lease_expires_at": receipt.lease_expires_at,
            "processed_at": receipt.processed_at, "quarantine_reason_code": receipt.quarantine_reason_code,
            "conflicting_envelope_json": (receipt.conflicting_envelope.model_dump_json() if receipt.conflicting_envelope else None),
            "conflicting_envelope_hash": (receipt.conflicting_envelope.envelope_hash if receipt.conflicting_envelope else None),
            "conflict_detected_at": receipt.conflict_detected_at,
            "last_error_code": receipt.last_error_code, "last_error_message": receipt.last_error_message,
            "updated_at": receipt.updated_at,
        }, not_found_message="Integration inbox receipt not found.", stale_message="Integration inbox receipt was changed concurrently.", extra_filters={"tenant_id": ctx.tenant_id, "organization_id": ctx.organization_id})

    def flush(self) -> None:
        self.session.flush()

    @staticmethod
    def _require_scope(receipt: IntegrationInboxReceipt, ctx: Any) -> None:
        if receipt.tenant_id != ctx.tenant_id or receipt.organization_id != ctx.organization_id:
            raise BusinessRuleError("Integration receipt is outside the active scope.", code="INTEGRATION_SCOPE_VIOLATION")

    @staticmethod
    def _from_row(row: Any) -> IntegrationInboxReceipt:
        conflicting_envelope = (
            IntegrationEventEnvelope.model_validate_json(row.conflicting_envelope_json)
            if row.conflicting_envelope_json else None
        )
        if conflicting_envelope and conflicting_envelope.envelope_hash != row.conflicting_envelope_hash:
            raise BusinessRuleError("Persisted conflicting envelope failed its integrity check.", code="INTEGRATION_ENVELOPE_INTEGRITY_FAILED")
        return IntegrationInboxReceipt(
            id=row.id, consumer_name=row.consumer_name, envelope=_envelope(row),
            deduplication_key=row.deduplication_key, status=row.status,
            attempt_count=row.attempt_count, max_attempts=row.max_attempts,
            available_at=_aware(row.available_at), lease_token=row.lease_token,
            lease_expires_at=_aware(row.lease_expires_at), processed_at=_aware(row.processed_at),
            quarantine_reason_code=row.quarantine_reason_code, last_error_code=row.last_error_code,
            conflicting_envelope=conflicting_envelope, conflict_detected_at=_aware(row.conflict_detected_at),
            last_error_message=row.last_error_message, created_at=_aware(row.created_at),
            updated_at=_aware(row.updated_at), row_version=row.version,
        )


__all__ = ["SqlAlchemyIntegrationInboxRepository", "SqlAlchemyIntegrationOutboxRepository"]
