from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.procurement_consumer import (
    ProcurementFinancialConsumer,
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
        "EVENT_ID_CONTENT_CONFLICT",
        "INTEGRATION_SERVICE_ACCOUNT_INVALID",
        "INTEGRATION_SERVICE_PRINCIPAL_DISABLED",
        "INTEGRATION_SERVICE_PRINCIPAL_SCOPE_MISMATCH",
        "PROCUREMENT_FINANCIAL_EVENT_UNSUPPORTED",
        "PROCUREMENT_FINANCIAL_PROJECT_REQUIRED",
        "PROCUREMENT_FINANCIAL_PROJECT_TASK_MISMATCH",
        "PROCUREMENT_FINANCIAL_TASK_NOT_FOUND",
        "PROCUREMENT_FINANCE_WORKER_SCOPE_MISMATCH",
        "PROCUREMENT_RECEIPT_CORRECTION_CONTRACT_REQUIRED",
        "PROCUREMENT_RECEIPT_DEFAULT_COST_CODE_REQUIRED",
        "PROCUREMENT_RECEIPT_FX_PROVIDER_REQUIRED",
        "PROCUREMENT_RECEIPT_SCOPE_MISMATCH",
        "PROJECT_COMMITMENT_AMOUNT_BELOW_MATCHED",
        "PROJECT_COMMITMENT_COST_ENTRY_DIMENSION_MISMATCH",
        "PROJECT_COMMITMENT_COST_ENTRY_NOT_MATCHABLE",
        "PROJECT_COMMITMENT_DEFAULT_COST_CODE_REQUIRED",
        "PROJECT_COMMITMENT_RECEIPT_DIMENSION_MISMATCH",
        "PROJECT_COMMITMENT_RECEIPT_SOURCE_NOT_FOUND",
        "PROJECT_COMMITMENT_SOURCE_IDENTITY_CONFLICT",
        "PROJECT_COMMITMENT_SOURCE_OUT_OF_ORDER",
        "PROJECT_COMMITMENT_SOURCE_REPLAY_CONFLICT",
        "PROJECT_COMMITMENT_SOURCE_SCOPE_MISMATCH",
        "PROJECT_COMMITMENT_STATE_REGRESSION",
    }
)


class ProcurementFinancialDispatcher:
    """At-least-once Procurement transport with one fresh Finance UoW per delivery."""

    def __init__(
        self,
        *,
        session: Session,
        outbox_service: IntegrationOutboxService,
        uow_factory: FinanceGovernanceUnitOfWorkFactory,
        consumer_factory: Callable[
            [FinanceGovernanceUnitOfWork, ServicePrincipal],
            ProcurementFinancialConsumer,
        ],
        principal_resolver: Callable[[], ServicePrincipal],
    ) -> None:
        self._session = session
        self._outbox_service = outbox_service
        self._uow_factory = uow_factory
        self._consumer_factory = consumer_factory
        self._principal_resolver = principal_resolver

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
                disposition = self._consume_under_unit_of_work(record.envelope)
                if disposition in {
                    InboxDeliveryDisposition.READY,
                    InboxDeliveryDisposition.DUPLICATE_PROCESSED,
                }:
                    self._outbox_service.mark_published(
                        record.id,
                        lease_token=lease_token,
                    )
                    published += 1
                else:
                    self._outbox_service.mark_failed(
                        record.id,
                        lease_token=lease_token,
                        error_code=f"CONSUMER_{disposition.value.upper()}",
                        error_message=(
                            "PM Finance did not accept the Procurement delivery."
                        ),
                    )
                self._session.commit()
            except Exception as exc:
                self._session.rollback()
                error_code = str(
                    getattr(exc, "code", None) or type(exc).__name__.upper()
                )[:96]
                error_message = str(exc) or "Procurement financial delivery failed."
                try:
                    failure_disposition = self._record_failure(
                        record.envelope,
                        error_code=error_code,
                        error_message=error_message,
                    )
                    if failure_disposition is InboxDeliveryDisposition.DUPLICATE_PROCESSED:
                        self._outbox_service.mark_published(
                            record.id,
                            lease_token=lease_token,
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
                    logger.exception("Failed to record Procurement delivery failure")
                logger.warning(
                    "Procurement financial delivery failed event_id=%s",
                    record.envelope.event_id,
                    exc_info=True,
                )
        return published

    def _consume_under_unit_of_work(
        self,
        envelope: IntegrationEventEnvelope,
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
                    consumption = self._consumer_factory(uow, principal).consume(envelope)
                    inbox.mark_processed(decision.receipt.id)
                    for event in consumption.commitment_events:
                        uow.record_event(event)
                    for event in consumption.cost_entry_events:
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
                "Procurement Finance service principal is outside the event scope.",
                code="PROCUREMENT_FINANCE_WORKER_SCOPE_MISMATCH",
            )


class _UnitOfWorkClock:
    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)


__all__ = ["ProcurementFinancialDispatcher"]
