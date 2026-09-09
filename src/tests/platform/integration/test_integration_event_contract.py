from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.core.platform.integration import IntegrationEventEnvelope


def _event(**overrides) -> IntegrationEventEnvelope:
    values = {
        "event_id": "event-1",
        "event_type": "platform_time.timesheet_period.approved",
        "schema_version": 1,
        "tenant_id": "tenant-1",
        "organization_id": "org-1",
        "aggregate_type": "timesheet_period",
        "aggregate_id": "period-1",
        "aggregate_version": 3,
        "occurred_at": datetime(2026, 8, 2, 11, 0, tzinfo=timezone(timedelta(hours=2))),
        "correlation_id": "correlation-1",
        "payload": {"period_id": "period-1", "status": "APPROVED"},
    }
    values.update(overrides)
    return IntegrationEventEnvelope(**values)


def test_integration_event_envelope_normalizes_time_and_has_stable_deduplication() -> None:
    event = _event()
    replay = _event(payload={"status": "APPROVED", "period_id": "period-1"})

    assert event.occurred_at == datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)
    assert event.payload_hash == replay.payload_hash
    assert event.inbox_deduplication_key("pm-finance") == replay.inbox_deduplication_key(
        "pm-finance"
    )
    assert event.inbox_deduplication_key("pm-finance") != event.inbox_deduplication_key(
        "reporting"
    )


def test_integration_event_envelope_rejects_naive_time_and_invalid_versions() -> None:
    with pytest.raises(ValidationError):
        _event(occurred_at=datetime(2026, 8, 2, 9, 0))
    with pytest.raises(ValidationError, match="Schema version"):
        _event(schema_version=0)
    with pytest.raises(ValidationError, match="Aggregate version"):
        _event(aggregate_version=-1)
