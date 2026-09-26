from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ResourceIdentityFact:
    resource_id: str
    resource_name: str
    identity_user_id: str
    is_active: bool = True


class ResourceIdentityReader(Protocol):
    def resolve_resource_for_user(
        self,
        *,
        user_id: str,
        tenant_id: str,
        organization_id: str,
    ) -> ResourceIdentityFact | None: ...


__all__ = ["ResourceIdentityFact", "ResourceIdentityReader"]
