from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.access.domain import (
    ScopedAccessGrant,
    ScopedRolePolicy,
    ScopedRolePolicyRegistry,
)

if TYPE_CHECKING:
    from src.core.platform.access.application import AccessControlService

__all__ = [
    "AccessControlService",
    "ScopedAccessGrant",
    "ScopedRolePolicy",
    "ScopedRolePolicyRegistry",
]


def __getattr__(name: str):
    if name == "AccessControlService":
        from src.core.platform.access.application import AccessControlService

        return AccessControlService
    raise AttributeError(name)
