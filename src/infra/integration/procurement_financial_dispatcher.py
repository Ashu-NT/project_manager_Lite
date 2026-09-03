from __future__ import annotations

import logging
from datetime import timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.invalidation import (
    FinanceInvalidationScope,
)
from src.core.modules.project_management.application.financials.procurement_consumer import (
    ProcurementFinancialConsumer,
)
from src.core.platform.application.integration import (
    InboxDeliveryDisposition,
    IntegrationInboxService,
    IntegrationOutboxService,
)
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import PostCommitEventPublisher
from src.core.shared.events.domain_events import domain_events


logger = logging.getLogger(__name__)


class ProcurementFinancialDispatcher:
    """Database transport adapter between Procurement facts and PM Finance."""

    def __init__(
        self,
        *,
        session: Session,
        outbox_service: IntegrationOutboxService,
        inbox_service: IntegrationInboxService,
        consumer: ProcurementFinancialConsumer,
        post_commit_bus: PostCommitEventPublisher,
    ) -> None:
        self._session = session
        self._outbox_service = outbox_service
        self._inbox_service = inbox_service
        self._consumer = consumer
        self._post_commit_bus = post_commit_bus

    def dispatch_pending(self, *, limit: int = 50) -> int:
        lease_token = f"procurement-finance:{uuid4()}"
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
                consumption = None
                if decision.disposition is InboxDeliveryDisposition.READY:
                    consumption = self._consumer.consume(record.envelope)
                    self._inbox_service.mark_processed(decision.receipt.id)
                self._session.commit()
                if consumption is not None:
                    self._emit_refresh(
                        consumption,
                        tenant_id=record.envelope.tenant_id,
                        organization_id=str(record.envelope.organization_id),
                        event_id=record.envelope.event_id,
                    )
                if decision.disposition is InboxDeliveryDisposition.QUARANTINED:
                    self._outbox_service.mark_failed(
                        record.id,
                        lease_token=lease_token,
                        error_code="CONSUMER_QUARANTINED",
                        error_message="PM Finance quarantined the Procurement delivery.",
                    )
                else:
                    self._outbox_service.mark_published(
                        record.id, lease_token=lease_token
                    )
                    published += 1
                self._session.commit()
            except Exception as exc:
                self._session.rollback()
                error_code = str(
                    getattr(exc, "code", None) or type(exc).__name__.upper()
                )[:96]
                error_message = str(exc) or "Procurement financial delivery failed."
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
                    logger.exception("Failed to record Procurement delivery failure")
                logger.warning(
                    "Procurement financial delivery failed event_id=%s",
                    record.envelope.event_id,
                    exc_info=True,
                )
        return published

    def _emit_refresh(
        self,
        consumption,
        *,
        tenant_id: str,
        organization_id: str,
        event_id: str,
    ) -> None:
        scope = FinanceInvalidationScope(
            tenant_id=str(tenant_id),
            organization_id=organization_id,
            project_id=str(consumption.project_id),
        )
        try:
            if consumption.commitment_events:
                context = DomainEventContext(correlation_id=generate_id())
                for event in consumption.commitment_events:
                    self._post_commit_bus.publish(event, context)
            if consumption.cost_entry_changed:
                domain_events.cost_entries_changed.emit(scope)
        except Exception:
            # Refresh is process-local and follows the durable inbox commit.
            logger.exception(
                "Procurement Finance refresh hint failed event_id=%s", event_id
            )


__all__ = ["ProcurementFinancialDispatcher"]
