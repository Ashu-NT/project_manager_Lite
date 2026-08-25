"""ADR-005: the `Subscription` (dispose) protocol returned by every subscribe-style call in
this event architecture (`TransactionalEventSubscriber.subscribe`,
`PostCommitEventSubscriber.subscribe`, `ViewInvalidationChannel.subscribe`).

Deliberately minimal and technology-agnostic -- infrastructure adapters (in-process bus, Qt
adapter, a future web adapter) each implement this the same way without depending on each
other. Core Shared code never implements Qt-specific disposal (destroyed-signal wiring, etc.)
-- that is P6's job, in `src/ui_qml/`.
"""

from __future__ import annotations

from typing import Protocol


class Subscription(Protocol):
    def dispose(self) -> None: ...


__all__ = ["Subscription"]
