from __future__ import annotations

from dataclasses import dataclass


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
