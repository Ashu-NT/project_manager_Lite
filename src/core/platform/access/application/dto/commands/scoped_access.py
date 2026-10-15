from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScopedAccessGrantAssignCommand:
    scope_type: str
    scope_id: str
    user_id: str
    scope_role: str


@dataclass(frozen=True)
class ScopedAccessGrantRemoveCommand:
    scope_type: str
    scope_id: str
    user_id: str
