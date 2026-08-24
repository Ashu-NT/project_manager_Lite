from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourceCapabilityCountsDesktopDto:
    skill_count: int
    certification_count: int


__all__ = ["ResourceCapabilityCountsDesktopDto"]
