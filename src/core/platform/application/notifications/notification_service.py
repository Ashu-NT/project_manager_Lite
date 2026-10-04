from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.contract.port.notifications.notification_delivery import (
    NotificationDelivery,
)
from src.core.platform.contract.repositories.notifications.contracts import (
    NotificationRepository,
)
from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    UserTenantMembershipRepository,
)
from src.core.platform.domain.notifications import Notification
from src.core.platform.domain.security.auth.session import UserSessionContext


class NotificationService:
    """Authenticated personal reads; writes come only from committed delivery work."""

    def __init__(
        self,
        *,
        session: Session,
        notification_repo: NotificationRepository,
        user_session: UserSessionContext | None = None,
        delivery: NotificationDelivery | None = None,
        memberships: UserTenantMembershipRepository | None = None,
    ) -> None:
        self._session = session
        self._notification_repo = notification_repo
        self._user_session = user_session
        self._delivery = delivery
        self._memberships = memberships

    def list_my_notifications(
        self,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        principal = self._require_principal()
        self._drain_pending(principal.user_id)
        tenant_id, organization_id = self._scope(principal.user_id)
        return self._notification_repo.list_for_user(
            principal.user_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            unread_only=unread_only,
            limit=limit,
        )

    def mark_read(self, notification_id: str) -> Notification:
        principal = self._require_principal()
        tenant_id, organization_id = self._scope(principal.user_id)
        notification = self._notification_repo.get_for_user(
            str(notification_id or "").strip(), user_id=principal.user_id,
            tenant_id=tenant_id, organization_id=organization_id,
        )
        if notification is None:
            raise NotFoundError(
                "Notification not found.",
                code="NOTIFICATION_NOT_FOUND",
            )
        if notification.read_at is not None:
            return notification
        read_at = datetime.now(timezone.utc)
        self._notification_repo.mark_read(
            notification.id, user_id=principal.user_id,
            tenant_id=tenant_id, organization_id=organization_id, read_at=read_at,
        )
        self._session.commit()
        return replace(notification, read_at=read_at)

    def count_my_unread(self) -> int:
        principal = self._require_principal()
        self._drain_pending(principal.user_id)
        tenant_id, organization_id = self._scope(principal.user_id)
        return self._notification_repo.count_unread_for_user(
            principal.user_id, tenant_id=tenant_id, organization_id=organization_id,
        )

    def _scope(self, user_id: str) -> tuple[str | None, str | None]:
        if self._user_session is None:
            return None, None
        tenant_id = self._user_session.stored_active_tenant_id()
        if tenant_id and self._memberships is not None:
            active = any(
                membership.tenant_id == tenant_id and membership.status == "active"
                for membership in self._memberships.list_memberships_for_user(user_id)
            )
            if not active:
                return None, None
        return tenant_id, self._user_session.stored_active_organization_id() if tenant_id else None

    def _drain_pending(self, user_id: str) -> None:
        if self._delivery is None or self._user_session is None:
            return
        active_tenant, active_org = self._scope(user_id)
        if active_tenant:
            self._delivery.drain(tenant_id=active_tenant, organization_id=None)
        if active_tenant and active_org:
            self._delivery.drain(tenant_id=active_tenant, organization_id=active_org)

    def mark_all_read(self) -> int:
        principal = self._require_principal()
        tenant_id, organization_id = self._scope(principal.user_id)
        read_at = datetime.now(timezone.utc)
        updated = self._notification_repo.mark_all_read_for_user(
            principal.user_id, tenant_id=tenant_id,
            organization_id=organization_id, read_at=read_at,
        )
        self._session.commit()
        return updated

    def _require_principal(self):
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None:
            raise BusinessRuleError(
                "Authentication is required to view notifications.",
                code="AUTHENTICATION_REQUIRED",
            )
        return principal


__all__ = ["NotificationService"]
