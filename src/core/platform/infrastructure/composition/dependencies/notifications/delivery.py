"""Build Platform notification delivery with scoped fresh sessions."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.notifications.notification_service import (
    NotificationService,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.events.view_invalidation import (
    RecipientScope,
    ViewInvalidationHint,
)
from src.infra.composition.persistence.repositories import RepositoryBundle
from src.infra.events.in_process_view_invalidation_channel import (
    InProcessViewInvalidationChannel,
)
from src.infra.integration.notification_dispatcher import NotificationDispatcher
from src.infra.persistence.db.postgresql_rls import configure_session_rls_context


def build_notification_service(
    *,
    session: Session,
    repositories: RepositoryBundle,
    user_session: UserSessionContext,
    view_invalidation_channel: InProcessViewInvalidationChannel,
    recipient_policy: Callable[[Session, object], bool] | None,
) -> NotificationService:
    notification_session_factory = sessionmaker(bind=session.bind, future=True)

    def _notification_session() -> Session:
        delivery_session = notification_session_factory()
        configure_session_rls_context(delivery_session, user_session=user_session)
        return delivery_session

    def _notification_delivered(
        tenant_id: str, organization_id: str | None, recipient_id: str
    ) -> None:
        view_invalidation_channel.notify(
            ViewInvalidationHint(
                scope=RecipientScope(tenant_id, organization_id, recipient_id),
                category="notification",
                scope_code="notification",
                entity_type="notification",
                entity_id=recipient_id,
            )
        )

    return NotificationService(
        session=session,
        notification_repo=repositories.notification_repo,
        user_session=user_session,
        memberships=repositories.user_tenant_repo,
        delivery=NotificationDispatcher(
            session_factory=_notification_session,
            on_delivered=_notification_delivered,
            recipient_policy=recipient_policy,
        ),
    )
