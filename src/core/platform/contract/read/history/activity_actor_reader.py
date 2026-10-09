from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class ActivityActorKind(StrEnum):
    HUMAN = "human"
    DISABLED = "disabled"
    SERVICE = "service"
    MISSING = "missing"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class ActivityActorPresentation:
    kind: ActivityActorKind
    label: str


class ActivityActorReader(Protocol):
    def resolve_batch(
        self, *, tenant_id: str, actor_ids: tuple[str, ...]
    ) -> dict[str, ActivityActorPresentation]: ...


__all__ = ["ActivityActorKind", "ActivityActorPresentation", "ActivityActorReader"]
