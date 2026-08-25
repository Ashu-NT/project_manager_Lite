"""ADR-005 Section 3/6 (P5A): `OrganizationCreated` -- Platform's Organization capability's own
business event vocabulary.

Application-authored via `uow.record_event(...)` from `OrganizationService`
(platform_p5_event_discovery.md Section 8): Organization is not yet aggregate-shaped (a plain
validated dataclass with no `.rename()`/state-transition methods -- see
`src/core/platform/domain/master_data/org/organization.py`), and a creation fact has no prior
instance to record itself on regardless (ADR-005's aggregate-recording rule is about transitions
on an *existing* entity, not construction).

Pure business vocabulary only -- no ViewInvalidation import, no legacy `domain_events` Signal
import, no dispatch/execution metadata (`correlation_id`/`causation_id`/`command_id` live on
`DomainEventContext`, never duplicated here).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationCreated:
    tenant_id: str
    organization_id: str
    name: str
    code: str
    occurred_at: datetime


__all__ = ["OrganizationCreated"]
