from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrganizationSwitcherItemViewModel:
    id: str
    display_name: str
    organization_code: str
    status: str


__all__ = ["OrganizationSwitcherItemViewModel"]
