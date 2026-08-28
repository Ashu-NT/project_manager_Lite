from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrganizationSwitcherItemViewModel:
    id: str
    display_name: str
    organization_code: str
    is_enabled: bool


__all__ = ["OrganizationSwitcherItemViewModel"]
