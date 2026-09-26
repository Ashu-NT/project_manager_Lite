"""Authenticated external outcomes: one scoped Finance transaction per delivery."""

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select, text

from src.core.modules.project_management.application.financials.accounting.outcome_quarantine import (
    AccountingOutcomeQuarantine,
)
from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    BillingPreparationExternalOutcomeRecorded,
)
from src.core.modules.project_management.domain.financials.accounting.outcome_policy import (
    OutcomeRejectionReason,
    validate_outcome_transition,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillingExternalEventType,
    ProjectBillingExternalEvent,
)
from src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff import (
    ProjectAccountingHandoffORM,
    ProjectAccountingOutboxORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.billing import (
    ProjectBillingExternalEventORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox import (
    ProjectFinanceInboxORM,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWork,
)
from src.core.platform.application.integration import (
    InboxDeliveryDisposition,
    IntegrationInboxService,
)
from src.core.platform.application.integration.accounting.outcome_ingress import (
    AccountingIngressAuthenticationError,
)
from src.core.platform.application.security.identity.execution_principal import (
    resolve_execution_principal,
)
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds
from src.core.platform.contract.port.integration.accounting_outcomes import (
    AccountingOutcomeKind,
)
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyUserRepository,
)
from src.core.platform.infrastructure.persistence.repositories.security.identity.identity import (
    SqlAlchemyServicePrincipalRepository,
)
from src.core.platform.integration.accounting_events import (
    ACCOUNTING_OUTCOME_CONSUMER,
    accounting_outcome_envelope,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.infra.persistence.db.postgresql_rls import (
    configure_session_rls_context,
    worker_tenant_scope,
)


@dataclass(frozen=True)
class _Scope:
    tenant_id: str
    organization_id: str

    def require_active_scope_ids(self, *, operation_label):
        return ActiveScopeIds(self.tenant_id, self.organization_id)


class SqlAlchemyAccountingOutcomeConsumer:
    def __init__(
        self, *, session_factory, clock, transactional_dispatcher, post_commit_bus
    ):
        self._sessions = session_factory
        self._clock = clock
        self._dispatcher = transactional_dispatcher
        self._bus = post_commit_bus

    def consume(self, ingress):
        identity = ingress.connection
        scope = _Scope(identity.tenant_id, identity.organization_id)
        with worker_tenant_scope(
            tenant_id=scope.tenant_id, organization_id=scope.organization_id
        ):
            session = self._sessions()
            configure_session_rls_context(session, user_session=None)
            with SqlAlchemyFinanceGovernanceUnitOfWork(
                session=session,
                context=DomainEventContext(correlation_id=str(uuid4())),
                transactional_dispatcher=self._dispatcher,
                post_commit_bus=self._bus,
                tenant_context_service=scope,
                user_session=None,
            ) as uow:
                principal = resolve_execution_principal(
                    name=identity.principal_name,
                    scope=scope,
                    principal_repository=SqlAlchemyServicePrincipalRepository(
                        session, tenant_context_service=scope
                    ),
                    user_repository=SqlAlchemyUserRepository(session),
                )
                if session.get_bind().dialect.name == "postgresql":
                    session.execute(
                        text("SELECT set_config('app.user_id', :actor, true)"),
                        {"actor": principal.user_id},
                    )
                    session.execute(
                        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                        {
                            "key": f"accounting-inbound:{identity.tenant_id}:{identity.organization_id}:{identity.adapter_id}:{identity.connection_id}"
                        },
                    )
                # Serialize first receipt inserts without reversing the outbound
                # preparation/connector row-lock order. SQLite UoW owns BEGIN.
                config = uow.accounting_connectors.get()
                if (
                    config is None
                    or not config.enabled
                    or (config.adapter_id, config.connection_id)
                    != (identity.adapter_id, identity.connection_id)
                ):
                    raise AccountingIngressAuthenticationError()
                with worker_tenant_scope(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    actor_user_id=principal.user_id,
                ):
                    result = self._consume(session, uow, ingress, principal.user_id)
                    uow.commit()
                    return result

    def _quarantine(self, uow, ingress, actor, reason, *, project_id=None):
        receipt = AccountingOutcomeQuarantine(
            repository=uow.finance_inbox, clock=self._clock
        ).record(ingress, reason=reason)
        self._audit(
            uow,
            ingress,
            actor,
            result=reason.value,
            entity_id=receipt.id,
            project_id=project_id,
        )
        return "quarantined"

    def _consume(self, session, uow, ingress, actor):
        if ingress.rejection is not None:
            return self._quarantine(uow, ingress, actor, ingress.rejection)
        outcome = ingress.outcome
        envelope = accounting_outcome_envelope(ingress.connection, outcome)
        inbox = IntegrationInboxService(
            repository=uow.finance_inbox,
            consumer_name=ACCOUNTING_OUTCOME_CONSUMER,
            clock=self._clock,
        )
        decision = inbox.begin_delivery(envelope)
        if decision.disposition is InboxDeliveryDisposition.DUPLICATE_PROCESSED:
            return "duplicate"
        if decision.disposition is not InboxDeliveryDisposition.READY:
            reason = OutcomeRejectionReason.EVENT_CONTENT_CONFLICT
            if decision.receipt.quarantine_reason_code == "STALE_AGGREGATE_VERSION":
                latest = uow.finance_inbox.latest_processed_aggregate_version(
                    consumer_name=ACCOUNTING_OUTCOME_CONSUMER,
                    aggregate_type=envelope.aggregate_type,
                    aggregate_id=envelope.aggregate_id,
                )
                reason = (
                    OutcomeRejectionReason.SEQUENCE_CONFLICT
                    if latest == envelope.aggregate_version
                    else OutcomeRejectionReason.STALE_SEQUENCE
                )
            return self._quarantine(uow, ingress, actor, reason)
        identity = ingress.connection
        handoff = session.scalar(
            select(ProjectAccountingHandoffORM).where(
                ProjectAccountingHandoffORM.id == outcome.handoff_id,
                ProjectAccountingHandoffORM.tenant_id == identity.tenant_id,
                ProjectAccountingHandoffORM.organization_id == identity.organization_id,
            )
        )
        reason = None
        project_id = None
        if handoff is None:
            reason = OutcomeRejectionReason.FOREIGN_HANDOFF
        else:
            project_id = handoff.project_id
            row = session.scalar(
                select(ProjectAccountingOutboxORM).where(
                    ProjectAccountingOutboxORM.event_id == handoff.id,
                    ProjectAccountingOutboxORM.tenant_id == identity.tenant_id,
                    ProjectAccountingOutboxORM.organization_id
                    == identity.organization_id,
                    ProjectAccountingOutboxORM.project_id == project_id,
                )
            )
            preparation = uow.billing.get_preparation(
                handoff.preparation_id, for_update=True
            )
            if row is None or (row.target_adapter_id, row.target_connection_id) != (
                identity.adapter_id,
                identity.connection_id,
            ):
                reason = OutcomeRejectionReason.CONNECTOR_MISMATCH
            elif (
                preparation is None
                or preparation.project_id != project_id
                or handoff.approved_version != outcome.approved_source_version
                or handoff.payload_hash != outcome.handoff_payload_hash
            ):
                reason = OutcomeRejectionReason.SOURCE_MISMATCH
            else:
                previous = self._previous(session, preparation)
                # Sequenced aggregate identity is independent of the current ordering mode.
                from src.core.platform.integration.canonical_json import (
                    canonical_json_sha256,
                )

                aggregate_id = canonical_json_sha256(
                    {
                        "tenant_id": identity.tenant_id,
                        "organization_id": identity.organization_id,
                        "adapter_id": identity.adapter_id,
                        "connection_id": identity.connection_id,
                        "handoff_id": outcome.handoff_id,
                    }
                )
                previous_sequence = (
                    uow.finance_inbox.latest_processed_aggregate_version(
                        consumer_name=ACCOUNTING_OUTCOME_CONSUMER,
                        aggregate_type="accounting_handoff_outcome",
                        aggregate_id=aggregate_id,
                    )
                )
                reason = validate_outcome_transition(
                    previous=previous,
                    incoming=outcome.outcome,
                    previous_sequence=previous_sequence,
                    incoming_sequence=outcome.sequence,
                    authoritative_sequence=identity.authoritative_sequence,
                    transport_delivered=row.status == "published"
                    and row.transport_receipt_json is not None,
                )
        if reason is not None:
            inbox.quarantine(
                decision.receipt.id,
                reason_code=reason.value,
                message="Accounting outcome correlation or transition is invalid.",
            )
            return self._quarantine(uow, ingress, actor, reason, project_id=project_id)
        version = preparation.row_version
        if outcome.outcome is AccountingOutcomeKind.ACKNOWLEDGED:
            preparation.acknowledge(occurred_at=outcome.occurred_at)
        elif outcome.outcome is AccountingOutcomeKind.RECONCILED:
            preparation.reconcile(occurred_at=outcome.occurred_at)
        # External rejection is evidence, NOT PM approval rejection or cancellation.
        if outcome.outcome is not AccountingOutcomeKind.REJECTED:
            uow.billing.update_preparation(preparation, expected_row_version=version)
        kind = {
            AccountingOutcomeKind.ACKNOWLEDGED: BillingExternalEventType.DELIVERY_ACCEPTED,
            AccountingOutcomeKind.REJECTED: BillingExternalEventType.DELIVERY_REJECTED,
            AccountingOutcomeKind.RECONCILED: BillingExternalEventType.RECONCILED,
        }[outcome.outcome]
        event = ProjectBillingExternalEvent.create(
            tenant_id=identity.tenant_id,
            organization_id=identity.organization_id,
            project_id=project_id,
            preparation_id=preparation.id,
            event_type=kind,
            external_system="external_accounting",
            external_status=outcome.outcome.value,
            idempotency_key=envelope.event_id,
            occurred_at=outcome.occurred_at,
            reconciliation_reference=outcome.reconciliation_reference,
            recorded_at=self._clock.now(),
        )
        uow.billing.add_external_event(event)
        receipt_row = session.get(ProjectFinanceInboxORM, decision.receipt.id)
        receipt_row.source_project_id = project_id
        inbox.mark_processed(decision.receipt.id)
        self._audit(
            uow,
            ingress,
            actor,
            result=outcome.outcome.value,
            entity_id=handoff.id,
            project_id=project_id,
        )
        uow.record_event(
            BillingPreparationExternalOutcomeRecorded(
                tenant_id=identity.tenant_id,
                organization_id=identity.organization_id,
                project_id=project_id,
                billing_preparation_id=preparation.id,
                external_event_id=event.id,
                event_type=kind,
                occurred_at=self._clock.now(),
            )
        )
        return "processed"

    @staticmethod
    def _previous(session, preparation):
        rejected = session.scalar(
            select(ProjectBillingExternalEventORM.id)
            .where(
                ProjectBillingExternalEventORM.tenant_id == preparation.tenant_id,
                ProjectBillingExternalEventORM.organization_id
                == preparation.organization_id,
                ProjectBillingExternalEventORM.project_id == preparation.project_id,
                ProjectBillingExternalEventORM.preparation_id == preparation.id,
                ProjectBillingExternalEventORM.event_type
                == BillingExternalEventType.DELIVERY_REJECTED.value,
            )
            .limit(1)
        )
        if rejected is not None:
            return AccountingOutcomeKind.REJECTED
        return {
            "acknowledged": AccountingOutcomeKind.ACKNOWLEDGED,
            "reconciled": AccountingOutcomeKind.RECONCILED,
        }.get(preparation.status.value)

    @staticmethod
    def _audit(uow, ingress, actor, *, result, entity_id, project_id):
        identity = ingress.connection
        uow._enterprise_audit_service.record(
            operation="accounting_outcome.consume",
            entity_type="AccountingHandoff",
            entity_id=entity_id,
            entity_parent_id=project_id,
            module="project_management",
            category="FINANCIAL",
            actor_id=actor,
            actor_type="service",
            source="ACCOUNTING_INGRESS",
            project_id=project_id,
            commit=False,
            after_data={
                "adapter_id": identity.adapter_id,
                "connection_id": identity.connection_id,
                "result": result,
                "body_sha256": ingress.body_sha256,
                "event_id": ingress.outcome.external_event_id
                if ingress.outcome
                else None,
                "sequence": ingress.outcome.sequence if ingress.outcome else None,
            },
        )
