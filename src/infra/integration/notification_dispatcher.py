"""Local, fresh-transaction consumer for durable in-app Notification work."""

import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.core.platform.domain.notifications import Notification
from src.core.platform.infrastructure.persistence.repositories.notifications.notification import (
    SqlAlchemyNotificationRepository,
)
from src.core.platform.infrastructure.persistence.repositories.notifications.notification_work import (
    next_notification_work,
)
from src.infra.persistence.db.postgresql_rls import worker_tenant_scope

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    def __init__(self, *, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def drain(self, *, tenant_id: str, organization_id: str | None, limit: int = 50) -> int:
        processed = 0
        for _ in range(max(0, min(int(limit), 200))):
            with worker_tenant_scope(tenant_id=tenant_id, organization_id=organization_id):
                with self._session_factory() as session:
                    candidate = next_notification_work(
                        session, tenant_id=tenant_id, organization_id=organization_id,
                        lock=False,
                    )
                    if candidate is None:
                        break
                    work_id = candidate.id
                    recipient_user_id = candidate.recipient_user_id
            with worker_tenant_scope(
                tenant_id=tenant_id, organization_id=organization_id,
                actor_user_id=recipient_user_id,
            ):
                with self._session_factory() as session:
                    work = next_notification_work(
                        session, tenant_id=tenant_id, organization_id=organization_id,
                        work_id=work_id,
                    )
                    if work is None or work.recipient_user_id != recipient_user_id:
                        continue
                    try:
                        with session.begin_nested():
                            notification = Notification.create(
                                recipient_user_id=work.recipient_user_id,
                                tenant_id=work.tenant_id,
                                organization_id=work.organization_id,
                                source_event_id=work.source_event_id,
                                category=work.category,
                                title=work.title,
                                body=work.body,
                                metadata=json.loads(work.metadata_json),
                            )
                            SqlAlchemyNotificationRepository(session).add_idempotent(notification)
                        work.status = "processed"
                        work.processed_at = datetime.now(timezone.utc)
                        session.commit()
                        processed += 1
                    except (ValueError, TypeError, json.JSONDecodeError):
                        work.status = "quarantined"
                        work.last_error_code = "INVALID_NOTIFICATION_WORK"
                        session.commit()
                    except Exception:
                        logger.exception("Notification delivery failed work_id=%s", work.id)
                        work.attempt_count += 1
                        work.status = "dead_letter" if work.attempt_count >= 8 else "retry"
                        work.available_at = datetime.now(timezone.utc) + timedelta(
                            seconds=min(900, 5 * (2 ** (work.attempt_count - 1)))
                        )
                        work.last_error_code = "DELIVERY_FAILED"
                        session.commit()
        return processed
