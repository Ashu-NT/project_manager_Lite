from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ScopeTypeChoiceDto:
    label: str
    value: str
    enabled: bool = True
    supporting_text: str = ""


@dataclass(frozen=True)
class ScopeTargetDto:
    id: str
    label: str
    scope_type: str
    supporting_text: str = ""


@dataclass(frozen=True)
class ScopedAccessGrantDto:
    id: str
    scope_type: str
    scope_id: str
    user_id: str
    scope_role: str
    permission_codes: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime | None = None


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
