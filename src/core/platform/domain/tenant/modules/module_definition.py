from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformCapability:
    code: str
    label: str
    description: str
    always_on: bool = True


@dataclass(frozen=True)
class EnterpriseModule:
    code: str
    label: str
    description: str
    default_enabled: bool = False
    stage: str = "planned"
    primary_capabilities: tuple[str, ...] = ()


__all__ = ["EnterpriseModule", "PlatformCapability"]
