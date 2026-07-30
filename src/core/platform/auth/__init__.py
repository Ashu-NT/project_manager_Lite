from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.platform.auth.application import AuthService, RoleGovernanceService
    from src.core.platform.auth.domain import UserSessionContext, UserSessionPrincipal

__all__ = [
    "AuthService",
    "RoleGovernanceService",
    "UserSessionContext",
    "UserSessionPrincipal",
]


def __getattr__(name: str):
    if name == "AuthService":
        from src.core.platform.auth.application import AuthService

        return AuthService
    if name == "RoleGovernanceService":
        from src.core.platform.auth.application import RoleGovernanceService

        return RoleGovernanceService
    if name == "UserSessionContext":
        from src.core.platform.auth.domain import UserSessionContext

        return UserSessionContext
    if name == "UserSessionPrincipal":
        from src.core.platform.auth.domain import UserSessionPrincipal

        return UserSessionPrincipal
    raise AttributeError(name)
