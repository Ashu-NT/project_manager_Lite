"""ADR-005 §4: the `DomainEvent` marker Protocol.

Structural typing only -- DomainEvent has no dispatch behavior of its own to test; these tests
confirm it is a pure, runtime-checkable typing contract with zero business/tenant/organization
vocabulary, and that a business-fact-shaped dataclass satisfies it structurally without ever
subclassing it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.shared.events.domain_event import DomainEvent


def test_domain_event_is_a_runtime_checkable_protocol() -> None:
    assert isinstance(DomainEvent, type)
    assert getattr(DomainEvent, "_is_protocol", False) is True
    assert getattr(DomainEvent, "_is_runtime_protocol", False) is True


def test_a_worked_business_event_satisfies_domain_event_structurally() -> None:
    """A concrete module event never subclasses DomainEvent -- it only needs to declare an
    `occurred_at: datetime` attribute to satisfy the Protocol structurally (duck typing),
    per ADR-005 §4."""

    @dataclass(frozen=True, slots=True, kw_only=True)
    class SomeWorkedEvent:
        occurred_at: datetime

    event = SomeWorkedEvent(occurred_at=datetime.now(timezone.utc))
    assert isinstance(event, DomainEvent)


def test_an_object_missing_occurred_at_does_not_satisfy_domain_event() -> None:
    class NotAnEvent:
        pass

    assert not isinstance(NotAnEvent(), DomainEvent)


def test_domain_event_protocol_declares_no_business_or_scope_vocabulary() -> None:
    """DomainEvent is a typing contract only -- it must never grow tenant_id/organization_id
    or any business field of its own (ADR-005 §4). Those belong on each module's own
    concrete event dataclasses.

    `occurred_at` is declared as a read-only `@property` (not a plain class-level attribute
    annotation), so it does not appear in `DomainEvent.__annotations__` -- Protocol member
    presence is checked directly instead."""
    annotations = getattr(DomainEvent, "__annotations__", {})
    assert annotations == {}
    public_members = {
        name
        for name in vars(DomainEvent)
        if not name.startswith("_")
    }
    assert public_members == {"occurred_at"}
    assert isinstance(vars(DomainEvent)["occurred_at"], property)
