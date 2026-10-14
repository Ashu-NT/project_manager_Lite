from __future__ import annotations

from src.core.platform.application.security.auth.queries.auth_queries import (
    AuthQueryHandler,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    TargetUserAuthorization,
)
from src.core.platform.contract.repositories.security.auth import AuthSessionRepository
from src.core.platform.domain.security.auth import AuthSession
from src.core.platform.domain.security.auth.session import UserSessionContext


class AuthSessionQueryHandler:
    """Reads a user's persisted Auth sessions within the actor's tenant."""

    def __init__(
        self,
        *,
        auth_queries: AuthQueryHandler,
        auth_session_repo: AuthSessionRepository | None,
        user_session: UserSessionContext | None,
        target_users: TargetUserAuthorization,
    ) -> None:
        self._auth_queries = auth_queries
        self._auth_session_repo = auth_session_repo
        self._user_session = user_session
        self._target_users = target_users

    def list_user_sessions(self, user_id: str) -> list[AuthSession]:
        require_any_permission(
            self._user_session,
            ("auth.read", "auth.manage", "security.manage"),
            operation_label="list user sessions",
        )
        self._target_users.require_target_user_in_active_tenant(
            user_id,
            operation_label="list sessions",
        )
        user = self._auth_queries.require_user(user_id)
        if self._auth_session_repo is None:
            return []
        return self._auth_session_repo.list_by_user(user.id)


__all__ = ["AuthSessionQueryHandler"]
