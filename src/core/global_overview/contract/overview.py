from __future__ import annotations

from dataclasses import dataclass

from src.core.application.global_overview.contracts.action_center import (
    ActionCenterSummaryDto,
)

# The four attention KPI counts are the same normalized counts the Action
# Center panel itself is built from -- reusing the one type here, rather than
# a second near-identical dataclass, keeps that guarantee structural instead
# of just documented.
AttentionSummaryDto = ActionCenterSummaryDto


@dataclass(frozen=True, slots=True)
class GlobalOverviewContextDto:
    tenant_name: str
    organization_name: str
    role_label: str | None = None


@dataclass(frozen=True, slots=True)
class GlobalOverviewCapabilitiesDto:
    """Generic, cross-cutting session capability inputs for presentation
    layers (e.g. deriving Quick Actions) -- never role names, and never a
    module-specific or action-specific decision. Deciding which concrete
    actions/cards to show from these inputs is a presentation concern, not
    an application-layer one."""

    effective_permissions: frozenset[str]
    accessible_module_codes: tuple[str, ...]


__all__ = ["AttentionSummaryDto", "GlobalOverviewCapabilitiesDto", "GlobalOverviewContextDto"]
