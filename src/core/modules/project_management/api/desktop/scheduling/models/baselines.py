from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SchedulingBaselineOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class SchedulingBaselineRowDto:
    id: str
    name: str
    created_at: date | None
    created_at_label: str
    approved_by_label: str
    variance_state_label: str
    status: str
    status_label: str
    can_submit: bool
    can_approve: bool
    can_reject: bool






__all__ = ['SchedulingBaselineOptionDescriptor', 'SchedulingBaselineRowDto']
