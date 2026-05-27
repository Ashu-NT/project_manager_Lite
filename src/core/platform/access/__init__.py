from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.access.contracts import (
    ProjectMembershipRepository,
    ScopedAccessGrantRepository,
)
from src.core.platform.access.domain import (
    ProjectMembership,
    ScopedAccessGrant,
    ScopedRolePolicy,
    ScopedRolePolicyRegistry,
)

if TYPE_CHECKING:
    from src.core.platform.access.application import AccessControlService

__all__ = [
    "AccessControlService",
    "ProjectMembership",
    "ProjectMembershipRepository",
    "ScopedAccessGrant",
    "ScopedAccessGrantRepository",
    "ScopedRolePolicy",
    "ScopedRolePolicyRegistry",
]


def __getattr__(name: str):
    if name == "AccessControlService":
        from src.core.platform.access.application import AccessControlService

        return AccessControlService
    raise AttributeError(name)
