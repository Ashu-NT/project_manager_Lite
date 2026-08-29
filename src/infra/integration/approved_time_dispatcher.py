from __future__ import annotations

import logging
from datetime import timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.invalidation import (
    FinanceInvalidationScope,
)
from src.core.modules.project_management.application.financials.cost.entries.approved_time_consumer import ApprovedTimeLaborCostConsumer
from src.core.shared.events.domain_events import domain_events
from src.core.platform.application.integration import InboxDeliveryDisposition, IntegrationInboxService, IntegrationOutboxService


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
                posted_entry = None
                if decision.disposition is InboxDeliveryDisposition.READY:
                    posted_entry = self._consumer.consume(record.envelope)
                    self._inbox_service.mark_processed(decision.receipt.id)
                self._session.commit()
                if posted_entry is not None:
                    self._emit_refresh(posted_entry, event_id=record.envelope.event_id)
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

    @staticmethod
    def _emit_refresh(entry, *, event_id: str) -> None:
        try:
            domain_events.cost_entries_changed.emit(
                FinanceInvalidationScope(
                    tenant_id=str(entry.tenant_id),
                    organization_id=str(entry.organization_id),
                    project_id=str(entry.project_id),
                )
            )
        except Exception:
            # The integration transaction is already committed; a process-local
            # presentation hint must never turn durable delivery into a retry.
            logger.exception(
                "Approved Time Finance refresh hint failed event_id=%s", event_id
            )


__all__ = ["ApprovedTimeFinancialDispatcher"]
