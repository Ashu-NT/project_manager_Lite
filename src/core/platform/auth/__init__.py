from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.platform.application.security.auth import AuthService
    from src.core.platform.application.security.authorization.roles import (
        RoleGovernanceService,
        TenantRoleAdministrationService,
    )
    from src.core.platform.domain.security.auth import UserSessionContext, UserSessionPrincipal

__all__ = [
    "AuthService",
    "RoleGovernanceService",
    "TenantRoleAdministrationService",
    "UserSessionContext",
    "UserSessionPrincipal",
]


def __getattr__(name: str):
    if name == "AuthService":
        from src.core.platform.application.security.auth import AuthService

        return AuthService
    if name == "RoleGovernanceService":
        from src.core.platform.application.security.authorization.roles import (
            RoleGovernanceService,
        )

        return RoleGovernanceService
    if name == "TenantRoleAdministrationService":
        from src.core.platform.application.security.authorization.roles import (
            TenantRoleAdministrationService,
        )

        return TenantRoleAdministrationService
    if name == "UserSessionContext":
        from src.core.platform.domain.security.auth import UserSessionContext

        return UserSessionContext
    if name == "UserSessionPrincipal":
        from src.core.platform.domain.security.auth import UserSessionPrincipal

        return UserSessionPrincipal
    raise AttributeError(name)
