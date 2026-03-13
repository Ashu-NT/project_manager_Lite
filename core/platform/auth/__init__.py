from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.platform.auth.service import AuthService
    from core.platform.auth.session import UserSessionContext, UserSessionPrincipal

__all__ = ["AuthService", "UserSessionPrincipal", "UserSessionContext"]


def __getattr__(name: str):
    if name == "AuthService":
        from core.platform.auth.service import AuthService

        return AuthService
    if name == "UserSessionContext":
        from core.platform.auth.session import UserSessionContext

        return UserSessionContext
    if name == "UserSessionPrincipal":
        from core.platform.auth.session import UserSessionPrincipal

        return UserSessionPrincipal
    raise AttributeError(name)
