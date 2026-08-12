from __future__ import annotations

import logging
from datetime import timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.cost.entries.approved_time_consumer import ApprovedTimeLaborCostConsumer
from src.core.platform.application.integration import InboxDeliveryDisposition, IntegrationInboxService, IntegrationOutboxService
from src.core.shared.events.domain_events import domain_events


logger = logging.getLogger(__name__)


class ApprovedTimeFinancialDispatcher:
    """Database transport adapter; business modules remain unaware of each other."""

    def __init__(
        self,
        *,
        session: Session,
        outbox_service: IntegrationOutboxService,
        inbox_service: IntegrationInboxService,
        consumer: ApprovedTimeLaborCostConsumer,
    ) -> None:
        self._session = session
        self._outbox_service = outbox_service
        self._inbox_service = inbox_service
        self._consumer = consumer

    def dispatch_pending(self, *, limit: int = 50) -> int:
        lease_token = f"approved-time:{uuid4()}"
        claimed = self._outbox_service.claim_batch(
            lease_token=lease_token,
            lease_duration=timedelta(minutes=2),
            limit=limit,
        )
        self._session.commit()
        published = 0
        for record in claimed:
            try:
                decision = self._inbox_service.begin_delivery(record.envelope)
                project_id = None
                if decision.disposition is InboxDeliveryDisposition.READY:
                    entry = self._consumer.consume(record.envelope)
                    project_id = entry.project_id
                    self._inbox_service.mark_processed(decision.receipt.id)
                self._session.commit()
                if decision.disposition is InboxDeliveryDisposition.QUARANTINED:
                    self._outbox_service.mark_failed(
                        record.id,
                        lease_token=lease_token,
                        error_code="CONSUMER_QUARANTINED",
                        error_message="PM Finance quarantined the Approved Time delivery.",
                    )
                else:
                    self._outbox_service.mark_published(record.id, lease_token=lease_token)
                    published += 1
                self._session.commit()
                if project_id:
                    try:
                        domain_events.cost_entries_changed.emit(project_id)
                    except Exception:
                        logger.warning(
                            "Approved Time posting committed but local cost refresh failed "
                            "project_id=%s",
                            project_id,
                            exc_info=True,
                        )
            except Exception as exc:
                self._session.rollback()
                error_code = str(
                    getattr(exc, "code", None) or type(exc).__name__.upper()
                )[:96]
                error_message = str(exc) or "Approved Time financial delivery failed."
                try:
                    failure_decision = self._inbox_service.begin_delivery(record.envelope)
                    if failure_decision.disposition is InboxDeliveryDisposition.READY:
                        self._inbox_service.record_failure(
                            failure_decision.receipt.id,
                            error_code=error_code,
                            error_message=error_message,
                        )
                    self._outbox_service.mark_failed(
                        record.id,
                        lease_token=lease_token,
                        error_code=error_code,
                        error_message=error_message,
                    )
                    self._session.commit()
                except Exception:
                    self._session.rollback()
                    logger.exception("Failed to record Approved Time delivery failure")
                logger.warning("Approved Time financial delivery failed event_id=%s", record.envelope.event_id, exc_info=True)
        return published


__all__ = ["ApprovedTimeFinancialDispatcher"]
