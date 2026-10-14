from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.security.auth import (
    normalize_auth_federated_subject,
    normalize_auth_identity_provider,
)
from src.core.platform.domain.security.auth.events import FederatedIdentityLinked


def normalize_identity_provider(identity_provider: str | None) -> str | None:
    return normalize_auth_identity_provider(identity_provider)


def normalize_federated_subject(federated_subject: str | None) -> str | None:
    return normalize_auth_federated_subject(federated_subject)


def validate_federated_identity(
    identity_provider: str | None,
    federated_subject: str | None,
) -> None:
    if identity_provider and federated_subject:
        return
    if identity_provider or federated_subject:
        raise ValidationError(
            "Identity provider and federated subject must be set together.",
            code="FEDERATED_IDENTITY_INCOMPLETE",
        )
from src.core.platform.application.security.auth.audit.security_audit import (
    SecurityAuditRecorder,
)
from src.core.platform.application.security.auth.auth_transaction_scope import (
    AuthTransactionScope,
)
from src.core.platform.application.security.auth.queries.auth_queries import (
    AuthQueryHandler,
)
from src.core.platform.application.security.auth.session.session_lifecycle import (
    AuthSessionLifecycle,
)
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    TargetUserAuthorization,
)
from src.core.platform.contract.repositories.security.auth import UserRepository
from src.core.platform.domain.security.auth.session import UserSessionContext

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount


class FederatedIdentityCommandHandler:
    """Links an external identity-provider subject to a user account."""

    def __init__(
        self,
        *,
        tx: AuthTransactionScope,
        auth_queries: AuthQueryHandler,
        user_repo: UserRepository,
        user_session: UserSessionContext | None,
        target_users: TargetUserAuthorization,
        audit: SecurityAuditRecorder,
        lifecycle: AuthSessionLifecycle,
    ) -> None:
        self._tx = tx
        self._auth_queries = auth_queries
        self._user_repo = user_repo
        self._user_session = user_session
        self._target_users = target_users
        self._audit = audit
        self._lifecycle = lifecycle

    def link_federated_identity(
        self,
        user_id: str,
        *,
        identity_provider: str,
        federated_subject: str,
    ) -> UserAccount:

        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="link federated identity",
        )
        self._target_users.require_target_user_in_active_tenant(
            user_id,
            operation_label="link federated identity",
        )
        user = self._auth_queries.require_user(user_id)
        normalized_provider = normalize_identity_provider(identity_provider)
        normalized_subject = normalize_federated_subject(federated_subject)
        validate_federated_identity(normalized_provider, normalized_subject)
        # Clearing a link (both absent) has no identity to collide with.
        existing = (
            self._user_repo.get_by_federated_identity(normalized_provider, normalized_subject)
            if normalized_provider and normalized_subject
            else None
        )
        if existing is not None and existing.id != user.id:
            raise ValidationError(
                "Federated identity is already linked to another user.",
                code="FEDERATED_IDENTITY_EXISTS",
            )
        updated_user = replace(
            user,
            identity_provider=identity_provider,
            federated_subject=federated_subject,
            updated_at=datetime.now(UTC),
        )
        with self._tx.uow() as uow:
            self._user_repo.update(updated_user)
            self._audit.add_atomic_security_audit(
                operation="update",
                entity_type="user",
                entity_id=updated_user.id,
                action="federated_identity.link",
                severity="high",
                field="identity_provider",
                old_value=user.identity_provider,
                new_value=updated_user.identity_provider,
            )
            uow.record_event(
                FederatedIdentityLinked(
                    user_id=updated_user.id,
                    tenant_id=self._tx.active_tenant_id_for_event(),
                    identity_provider=str(updated_user.identity_provider or ""),
                    occurred_at=updated_user.updated_at or datetime.now(UTC),
                )
            )
            uow.commit()
        self._lifecycle.refresh_current_session_if_user(updated_user.id)
        return updated_user


__all__ = ["FederatedIdentityCommandHandler"]
