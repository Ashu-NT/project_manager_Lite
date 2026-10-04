"""Local, fresh-transaction consumer for durable in-app Notification work."""

import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.domain.notifications import Notification
from src.core.platform.infrastructure.persistence.common.approval_eligibility import (
    approval_reviewer_eligibility,
)
from src.core.platform.infrastructure.persistence.common.scoped_permission import (
    scoped_permission,
)
from src.core.platform.infrastructure.persistence.orm.approval.approval import (
    ApprovalRequestORM,
)
from src.core.platform.infrastructure.persistence.orm.security.auth.auth import UserORM
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import (
    UserTenantORM,
)
from src.core.platform.infrastructure.persistence.repositories.notifications.notification import (
    SqlAlchemyNotificationRepository,
)
from src.core.platform.infrastructure.persistence.repositories.notifications.notification_work import (
    next_notification_work,
)
from src.infra.persistence.db.postgresql_rls import worker_tenant_scope

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        on_delivered: Callable[[str, str | None, str], None] | None = None,
        recipient_policy: Callable[[Session, object], bool] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._on_delivered = on_delivered
        self._recipient_policy = recipient_policy

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
                    if not self._recipient_is_current(session, work) or (
                        self._recipient_policy is not None
                        and not self._recipient_policy(session, work)
                    ):
                        work.status = "quarantined"
                        work.last_error_code = "RECIPIENT_NO_LONGER_ELIGIBLE"
                        session.commit()
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
                        delivered_scope = (
                            work.tenant_id, work.organization_id, work.recipient_user_id
                        )
                        session.commit()
                        processed += 1
                        if self._on_delivered is not None:
                            try:
                                self._on_delivered(*delivered_scope)
                            except Exception:
                                logger.exception("Notification delivery hint failed")
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

    @staticmethod
    def _recipient_is_current(session: Session, work) -> bool:
        active_user = session.scalar(select(UserORM.id).where(
            UserORM.id == work.recipient_user_id,
            UserORM.is_active.is_(True),
        ))
        if not active_user:
            return False
        membership = session.scalar(select(UserTenantORM).where(
            UserTenantORM.user_id == work.recipient_user_id,
            UserTenantORM.tenant_id == work.tenant_id,
        ))
        if membership is None:
            return False
        if membership.status != "active" or membership.revoked_at is not None:
            return False
        if not work.category.startswith("approval."):
            return True
        try:
            request_id = json.loads(work.metadata_json)["request_id"]
        except (KeyError, TypeError, ValueError):
            return False
        request = ApprovalRequestORM
        conditions = [
            request.id == request_id,
            request.tenant_id == work.tenant_id,
            request.organization_id == work.organization_id,
        ]
        if work.category == "approval.requested.v1":
            conditions.append(approval_reviewer_eligibility(work.recipient_user_id))
        elif work.category in {"approval.approved.v1", "approval.rejected.v1"}:
            conditions.extend((
                request.status == (
                    "APPROVED" if work.category == "approval.approved.v1" else "REJECTED"
                ),
                request.requested_by_user_id == work.recipient_user_id,
                scoped_permission(
                    user_id=work.recipient_user_id,
                    tenant_id=request.tenant_id,
                    organization_id=request.organization_id,
                    project_id=request.project_id,
                    permissions=("approval.request", "approval.decide"),
                ),
            ))
        else:
            return False
        return bool(session.scalar(select(request.id).where(*conditions)))
