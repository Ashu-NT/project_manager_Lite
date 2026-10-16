from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SchedulingProjectOptionDescriptor:
    value: str
    label: str


__all__ = ["SchedulingProjectOptionDescriptor"]
