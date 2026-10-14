from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.core.platform.domain.security.auth.datetime_utils import ensure_utc_datetime

logger = logging.getLogger(__name__)
from src.core.platform.application.security.auth.session.principal_builder import (
    PrincipalBuilder,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.contract.repositories.security.auth import (
    AuthSessionRepository,
    UserRepository,
)
from src.core.platform.domain.security.auth.session import (
    UserSessionContext,
    UserSessionPrincipal,
)

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount


class AuthSessionLifecycle:
    """Keeps persisted sessions and the in-process principal consistent with a
    user's current state: revokes sessions and rebuilds or clears the principal."""

    def __init__(
        self,
        *,
        user_repo: UserRepository,
        auth_session_repo: AuthSessionRepository | None,
        user_session: UserSessionContext | None,
        principals: PrincipalBuilder,
    ) -> None:
        self._user_repo = user_repo
        self._auth_session_repo = auth_session_repo
        self._user_session = user_session
        self._principals = principals

    def revoke_all_persisted_sessions(self, user: UserAccount, *, revoked_at: datetime) -> None:
        if self._auth_session_repo is None:
            return
        for auth_session in self._auth_session_repo.list_by_user(user.id):
            if auth_session.revoked_at is not None:
                continue
            auth_session.revoked_at = revoked_at
            auth_session.updated_at = revoked_at
            self._auth_session_repo.update(auth_session)

    def resolve_current_principal_session_id(self, user_id: str) -> str | None:
        if self._user_session is None:
            return None
        principal = self._user_session.principal
        if principal is None or principal.user_id != user_id:
            return None
        session_id = str(getattr(principal, "session_id", "") or "").strip() or None
        if session_id is None or self._auth_session_repo is None:
            return session_id
        auth_session = self._auth_session_repo.get(session_id)
        if auth_session is None or auth_session.revoked_at is not None:
            return None
        return session_id

    def refresh_current_session_if_user(self, user_id: str) -> None:
        if self._user_session is None:
            return
        principal = self._user_session.principal
        if principal is None or principal.user_id != user_id:
            return
        user = self._user_repo.get(user_id)
        if user is None or not user.is_active:
            self._user_session.clear()
            return
        session_expires_at = ensure_utc_datetime(user.session_expires_at)
        if session_expires_at is not None and datetime.now(UTC) >= session_expires_at:
            self._user_session.clear()
            return
        preferred_session_id = self.resolve_current_principal_session_id(user_id)
        current_session_id = str(getattr(principal, "session_id", "") or "").strip() or None
        if self._auth_session_repo is not None and current_session_id is not None and preferred_session_id is None:
            self._user_session.clear()
            return
        try:
            rebuilt = self._principals.build(
                user,
                session_id=preferred_session_id,
            )
        except Exception:
            logger.warning(
                "Current session authority refresh denied user_id=%s",
                user.id,
                exc_info=True,
            )
            self._user_session.clear()
            return
        self._user_session.set_principal(rebuilt)

    def rebuild_current_for_context(
        self,
        tenant_id: str,
        organization_id: str | None,
    ) -> UserSessionPrincipal:
        """Principal for the current user in a newly selected tenant/organization."""
        current = self._user_session.principal if self._user_session is not None else None
        if current is None:
            raise BusinessRuleError(
                "Authentication is required to rebuild tenant authority.",
                code="AUTHENTICATION_REQUIRED",
            )
        user = self._user_repo.get(current.user_id)
        if not user:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        return self._principals.build_for_context(
            user,
            tenant_id=tenant_id,
            organization_id=organization_id,
            session_id=current.session_id,
        )


__all__ = ["AuthSessionLifecycle"]
