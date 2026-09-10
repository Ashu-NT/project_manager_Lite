from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.cost.entries.approved_time_consumer import (
    ApprovedTimeLaborCostConsumer,
)
from src.core.modules.project_management.contracts.uow.finance.finance_governance_unit_of_work import (
    FinanceGovernanceUnitOfWork,
    FinanceGovernanceUnitOfWorkFactory,
)
from src.core.platform.application.integration import (
    InboxDeliveryDisposition,
    IntegrationInboxService,
    IntegrationOutboxService,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.identity.service_principal import ServicePrincipal
from src.core.platform.integration import IntegrationEventEnvelope
from src.core.shared.events.domain_event_context import DomainEventContext
from src.infra.persistence.db.postgresql_rls import worker_tenant_scope


logger = logging.getLogger(__name__)

_PERMANENT_FAILURE_CODES = frozenset(
    {
        "APPROVED_TIME_SCOPE_MISMATCH",
        "APPROVED_TIME_WORKER_SCOPE_MISMATCH",
        "APPROVED_TIME_SOURCE_HASH_CONFLICT",
        "APPROVED_TIME_STALE_REVISION",
        "APPROVED_TIME_CORRECTION_CHAIN_INVALID",
        "APPROVED_TIME_REVISION_GAP",
        "INTEGRATION_SERVICE_PRINCIPAL_SCOPE_MISMATCH",
        "INTEGRATION_SERVICE_PRINCIPAL_DISABLED",
        "INTEGRATION_SERVICE_ACCOUNT_INVALID",
    }
)


class ApprovedTimeFinancialDispatcher:
    """At-least-once transport with a fresh Finance transaction per delivery."""

    def __init__(
        self,
        *,
        session: Session,
        outbox_service: IntegrationOutboxService,
        uow_factory: FinanceGovernanceUnitOfWorkFactory,
        consumer_factory: Callable[
            [FinanceGovernanceUnitOfWork, ServicePrincipal],
            ApprovedTimeLaborCostConsumer,
        ],
        principal_resolver: Callable[[], ServicePrincipal],
    ) -> None:
        self._session = session
        self._outbox_service = outbox_service
        self._uow_factory = uow_factory
        self._consumer_factory = consumer_factory
        self._principal_resolver = principal_resolver
        self._transactional_dispatcher = uow_factory._transactional_dispatcher
        self._post_commit_bus = uow_factory._post_commit_bus

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
                disposition = self._consume_under_unit_of_work(record.envelope)
                if disposition in {
                    InboxDeliveryDisposition.READY,
                    InboxDeliveryDisposition.DUPLICATE_PROCESSED,
                }:
                    self._outbox_service.mark_published(
                        record.id, lease_token=lease_token
                    )
                    published += 1
                else:
                    self._outbox_service.mark_failed(
                        record.id,
                        lease_token=lease_token,
                        error_code=f"CONSUMER_{disposition.value.upper()}",
                        error_message=(
                            "PM Finance did not accept the Approved Time delivery."
                        ),
                    )
                self._session.commit()
            except Exception as exc:
                self._session.rollback()
                error_code = str(
                    getattr(exc, "code", None) or type(exc).__name__.upper()
                )[:96]
                error_message = str(exc) or "Approved Time financial delivery failed."
                try:
                    failure_disposition = self._record_failure(
                        record.envelope,
                        error_code=error_code,
                        error_message=error_message,
                    )
                    if failure_disposition is InboxDeliveryDisposition.DUPLICATE_PROCESSED:
                        self._outbox_service.mark_published(
                            record.id, lease_token=lease_token
                        )
                        published += 1
                    else:
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
                logger.warning(
                    "Approved Time financial delivery failed event_id=%s",
                    record.envelope.event_id,
                    exc_info=True,
                )
        return published

    def _consume_under_unit_of_work(
        self, envelope: IntegrationEventEnvelope
    ) -> InboxDeliveryDisposition:
        principal = self._principal_resolver()
        self._require_principal_scope(principal, envelope)
        with worker_tenant_scope(
            tenant_id=envelope.tenant_id,
            organization_id=envelope.organization_id,
            actor_user_id=principal.user_id,
        ):
            with self._uow_factory.create(context=self._event_context(envelope)) as uow:
                inbox = self._inbox_service(uow)
                decision = inbox.begin_delivery(envelope)
                if decision.disposition is InboxDeliveryDisposition.READY:
                    consumer = self._consumer_factory(uow, principal)
                    events = consumer.consume(envelope)
                    inbox.mark_processed(decision.receipt.id)
                    for event in events:
                        uow.record_event(event)
                uow.commit()
                return decision.disposition

    def _record_failure(
        self,
        envelope: IntegrationEventEnvelope,
        *,
        error_code: str,
        error_message: str,
    ) -> InboxDeliveryDisposition:
        with worker_tenant_scope(
            tenant_id=envelope.tenant_id,
            organization_id=envelope.organization_id,
        ):
            with self._uow_factory.create(context=self._event_context(envelope)) as uow:
                inbox = self._inbox_service(uow)
                decision = inbox.begin_delivery(envelope)
                if decision.disposition is InboxDeliveryDisposition.READY:
                    if error_code in _PERMANENT_FAILURE_CODES:
                        inbox.quarantine(
                            decision.receipt.id,
                            reason_code=error_code,
                            message=error_message,
                        )
                    else:
                        inbox.record_failure(
                            decision.receipt.id,
                            error_code=error_code,
                            error_message=error_message,
                        )
                uow.commit()
                return decision.disposition

    @staticmethod
    def _inbox_service(
        uow: FinanceGovernanceUnitOfWork,
    ) -> IntegrationInboxService:
        return IntegrationInboxService(
            repository=uow.finance_inbox,
            consumer_name="project_finance",
            clock=_UnitOfWorkClock(),
        )

    @staticmethod
    def _event_context(envelope: IntegrationEventEnvelope) -> DomainEventContext:
        return DomainEventContext(
            correlation_id=envelope.correlation_id or envelope.event_id,
            causation_id=envelope.causation_id or envelope.event_id,
        )

    @staticmethod
    def _require_principal_scope(
        principal: ServicePrincipal,
        envelope: IntegrationEventEnvelope,
    ) -> None:
        if (
            principal.tenant_id != envelope.tenant_id
            or principal.organization_id != envelope.organization_id
        ):
            raise BusinessRuleError(
                "Approved Time service principal is outside the event scope.",
                code="APPROVED_TIME_WORKER_SCOPE_MISMATCH",
            )


class _UnitOfWorkClock:
    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)


__all__ = ["ApprovedTimeFinancialDispatcher"]
