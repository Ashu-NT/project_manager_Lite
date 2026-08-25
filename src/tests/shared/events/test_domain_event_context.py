"""ADR-005 §5: `DomainEventContext` -- dispatch/execution metadata, kept independent from
business-fact content.
"""

from __future__ import annotations

import dataclasses

import pytest

from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext


def test_domain_event_context_requires_only_correlation_id() -> None:
    context = DomainEventContext(correlation_id="corr-1")
    assert context.correlation_id == "corr-1"
    assert context.causation_id is None
    assert context.command_id is None


def test_domain_event_context_accepts_optional_causation_and_command_ids() -> None:
    context = DomainEventContext(
        correlation_id="corr-1", causation_id="cause-1", command_id="cmd-1"
    )
    assert context.causation_id == "cause-1"
    assert context.command_id == "cmd-1"


def test_domain_event_context_is_frozen() -> None:
    context = DomainEventContext(correlation_id="corr-1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.correlation_id = "corr-2"  # type: ignore[misc]


def test_domain_event_context_is_positional_free_kw_only() -> None:
    with pytest.raises(TypeError):
        DomainEventContext("corr-1")  # type: ignore[misc, call-arg]


def test_domain_event_context_fields_are_disjoint_from_domain_event_fields() -> None:
    """ADR-005 §5: business-fact data and dispatch metadata are two different things, kept
    in two different places -- DomainEventContext must never declare a field that overlaps
    with DomainEvent's own vocabulary (occurred_at), and must never declare tenant_id or
    organization_id (those are business-fact fields per ADR-005 §3)."""
    context_fields = {f.name for f in dataclasses.fields(DomainEventContext)}
    domain_event_fields = set(getattr(DomainEvent, "__annotations__", {}))

    assert context_fields.isdisjoint(domain_event_fields)
    assert "tenant_id" not in context_fields
    assert "organization_id" not in context_fields
    assert "actor_id" not in context_fields, "actor identity is business-meaningful, not generic context (ADR-005 §5)"


def test_domain_event_context_has_no_schema_version() -> None:
    """ADR-005 §11: schema_version belongs exclusively to the durable IntegrationEventEnvelope
    (ADR-PF-011), never to in-process DomainEvent/DomainEventContext."""
    context_fields = {f.name for f in dataclasses.fields(DomainEventContext)}
    assert "schema_version" not in context_fields
