"""Fresh scoped claim/finalize transactions for the external delivery runtime."""

from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select, text

from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    AccountingTransportFinalized,
)
from src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff import (
    ProjectAccountingOutboxORM,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.accounting.handoff import (
    SqlAlchemyAccountingHandoffRepository,
    SqlAlchemyAccountingOutboxRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.invoicing.billing import (
    SqlAlchemyProjectBillingRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.application.integration.delivery_service import (
    IntegrationOutboxService,
)
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.port.integration.external_accounting import (
    ExternalAccountingEvidence,
    ExternalAccountingFailureKind,
    ExternalAccountingReceipt,
    ExternalAccountingTarget,
)
from src.core.platform.contract.uow.integration.accounting_delivery import (
    ClaimedAccountingDelivery,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.repositories.integration.accounting_connector import (
    SqlAlchemyAccountingConnectorRepository,
)
from src.core.platform.integration import OutboxDeliveryStatus
from src.core.platform.integration.canonical_json import canonical_json_bytes
from src.core.shared.events.domain_event_context import DomainEventContext
from src.infra.persistence.db.postgresql_rls import (
    configure_session_rls_context,
    worker_tenant_scope,
)
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase


@dataclass(frozen=True)
class AccountingWorkerScope:
    tenant_id: str
    organization_id: str
    project_id: str

    def __post_init__(self):
        if not all(
            (
                self.tenant_id.strip(),
                self.organization_id.strip(),
                self.project_id.strip(),
            )
        ):
            raise ValueError(
                "Explicit Accounting worker tenant, organization and project are required."
            )

    def require_active_scope_ids(self, *, operation_label):
        return ActiveScopeIds(self.tenant_id, self.organization_id)

    def get_active_tenant_id(self):
        return self.tenant_id

    def get_active_organization_id(self):
        return self.organization_id

    def active_tenant_id(self):
        return self.tenant_id

    def active_organization_id(self):
        return self.organization_id


class _ProjectOutbox(SqlAlchemyAccountingOutboxRepository):
    def __init__(self, session, project_id):
        super().__init__(session)
        self._project_id = project_id

    def _claim_scope_filters(self):
        return (ProjectAccountingOutboxORM.project_id == self._project_id,)


class SqlAlchemyAccountingDeliveryTransactions:
    def __init__(
        self,
        *,
        session_factory,
        scope: AccountingWorkerScope,
        authorize,
        capability_factory,
        clock,
        transactional_dispatcher,
        post_commit_bus,
        lease_duration=timedelta(seconds=120),
    ):
        self._session_factory = session_factory
        self._scope = scope
        self._authorize = authorize
        self._capability_factory = capability_factory
        self._clock = clock
        self._dispatcher = transactional_dispatcher
        self._bus = post_commit_bus
        self._lease_duration = lease_duration

    @contextmanager
    def _operation(self, *, correlation_id=None):
        scope = self._scope
        # Host-configured scope is reauthorized against the durable service identity.
        with worker_tenant_scope(
            tenant_id=scope.tenant_id, organization_id=scope.organization_id
        ):
            session = self._session_factory()
            configure_session_rls_context(session, user_session=None)
            with SqlAlchemyUnitOfWorkBase(
                session=session,
                context=DomainEventContext(
                    correlation_id=correlation_id or str(uuid4())
                ),
                transactional_dispatcher=self._dispatcher,
                post_commit_bus=self._bus,
            ) as uow:
                actor_id = self._authorize(session, scope)
                if session.get_bind().dialect.name == "postgresql":
                    session.execute(
                        text("SELECT set_config('app.user_id', :actor, true)"),
                        {"actor": actor_id},
                    )
                with worker_tenant_scope(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    actor_user_id=actor_id,
                ):
                    yield session, uow, actor_id

    def _repository(self, repository_type, session):
        repository = repository_type(session)
        repository._tenant_context_service = self._scope
        return repository

    def _outbox(self, session):
        repository = _ProjectOutbox(session, self._scope.project_id)
        repository._tenant_context_service = self._scope
        return repository, IntegrationOutboxService(
            repository=repository, owner_module="project_management", clock=self._clock
        )

    def claim(self):
        with self._operation() as (session, uow, _actor_id):
            _, service = self._outbox(session)
            records = service.claim_batch(
                lease_token=str(uuid4()), lease_duration=self._lease_duration, limit=1
            )
            if not records:
                uow.commit()
                return None
            record = records[0]
            row = self._row(session, record.id)
            snapshot = self._repository(
                SqlAlchemyAccountingHandoffRepository, session
            ).get_for_preparation(
                self._scope.project_id,
                record.envelope.aggregate_id,
            )
            if (
                snapshot is None
                or snapshot.handoff_id != record.envelope.event_id
                or (record.tenant_id, record.organization_id) != (self._scope.tenant_id, self._scope.organization_id)
                or snapshot.approved_preparation_version != record.envelope.aggregate_version
                or snapshot.canonical_bytes != canonical_json_bytes(record.envelope.payload)
            ):
                raise BusinessRuleError(
                    "Accounting handoff scope mismatch.",
                    code="INTEGRATION_SCOPE_VIOLATION",
                )
            evidence = ExternalAccountingEvidence(
                handoff_id=snapshot.handoff_id,
                tenant_id=self._scope.tenant_id,
                organization_id=self._scope.organization_id,
                project_id=self._scope.project_id,
                source_id=snapshot.evidence.preparation_id,
                source_version=snapshot.approved_preparation_version,
                schema_name=snapshot.schema_name,
                schema_version=1,
                payload_bytes=snapshot.canonical_bytes,
                payload_hash=snapshot.content_hash,
                correlation_id=record.envelope.correlation_id,
                causation_id=record.envelope.causation_id,
            )
            decision = self._capability_factory(session, self._scope).evaluate(
                authorized=True,
                eligible=True,
                for_update=True,
            )
            config = self._repository(
                SqlAlchemyAccountingConnectorRepository, session
            ).get(for_update=True)
            failure = None
            target = None
            secret_reference = None
            if not decision.allowed or config is None:
                failure = ExternalAccountingFailureKind.CONFIGURATION
            elif row.target_adapter_id is not None and (
                row.target_adapter_id != config.adapter_id
                or row.target_connection_id != config.connection_id
            ):
                failure = ExternalAccountingFailureKind.CONFIGURATION
            else:
                row.target_adapter_id = config.adapter_id
                row.target_connection_id = config.connection_id
                row.target_configuration_version = config.version
                target = ExternalAccountingTarget(
                    tenant_id=config.tenant_id,
                    organization_id=config.organization_id,
                    adapter_id=config.adapter_id,
                    connection_id=config.connection_id,
                    configuration_version=config.version,
                )
                secret_reference = config.secret_reference
            result = ClaimedAccountingDelivery(
                outbox_id=record.id,
                lease_token=record.lease_token,
                attempt_count=record.attempt_count,
                evidence=evidence,
                target=target,
                secret_reference=secret_reference,
                preflight_failure=failure,
            )
            uow.commit()
            return result

    def _row(self, session, record_id):
        row = session.scalars(
            select(ProjectAccountingOutboxORM)
            .where(
                ProjectAccountingOutboxORM.id == record_id,
                ProjectAccountingOutboxORM.tenant_id == self._scope.tenant_id,
                ProjectAccountingOutboxORM.organization_id
                == self._scope.organization_id,
                ProjectAccountingOutboxORM.project_id == self._scope.project_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one_or_none()
        if row is None:
            raise BusinessRuleError(
                "Accounting work is outside the worker scope.",
                code="INTEGRATION_SCOPE_VIOLATION",
            )
        return row

    def finalize(self, claim, result):
        if (
            claim.evidence.tenant_id,
            claim.evidence.organization_id,
            claim.evidence.project_id,
        ) != (
            self._scope.tenant_id,
            self._scope.organization_id,
            self._scope.project_id,
        ):
            raise BusinessRuleError(
                "Accounting result scope mismatch.", code="INTEGRATION_SCOPE_VIOLATION"
            )
        with self._operation(correlation_id=claim.evidence.correlation_id) as (
            session,
            uow,
            actor_id,
        ):
            row = self._row(session, claim.outbox_id)
            repository, service = self._outbox(session)
            record = repository.get(claim.outbox_id)
            record.require_lease(claim.lease_token, at=self._clock.now())
            if (
                record.envelope.event_id != claim.evidence.handoff_id
                or record.envelope.payload_hash != claim.evidence.payload_hash
                or record.envelope.aggregate_id != claim.evidence.source_id
                or record.envelope.aggregate_version != claim.evidence.source_version
                or canonical_json_bytes(record.envelope.payload)
                != claim.evidence.payload_bytes
                or record.envelope.payload.get("schema_name")
                != claim.evidence.schema_name
                or record.envelope.schema_version != claim.evidence.schema_version
            ):
                raise BusinessRuleError(
                    "Accounting result identity mismatch.",
                    code="ACCOUNTING_HANDOFF_CONTENT_CONFLICT",
                )
            now = self._clock.now()
            if isinstance(result, ExternalAccountingReceipt):
                if (
                    claim.target is None
                    or not result.matches(claim.evidence, claim.target)
                    or (
                        row.target_adapter_id,
                        row.target_connection_id,
                    )
                    != (result.adapter_id, result.connection_id)
                ):
                    raise BusinessRuleError(
                        "Accounting receipt mismatch.",
                        code="ACCOUNTING_RECEIPT_MISMATCH",
                    )
                service.mark_published(record.id, lease_token=claim.lease_token)
                row.transport_receipt_json = result.model_dump_json()
                billing = self._repository(SqlAlchemyProjectBillingRepository, session)
                preparation = billing.get_preparation(
                    claim.evidence.source_id, for_update=True
                )
                if (
                    preparation is None
                    or preparation.project_id != self._scope.project_id
                ):
                    raise BusinessRuleError(
                        "Accounting preparation mismatch.",
                        code="INTEGRATION_SCOPE_VIOLATION",
                    )
                version = preparation.row_version
                preparation.mark_delivered(occurred_at=now)
                billing.update_preparation(preparation, expected_row_version=version)
                outcome = "transport_accepted"
            elif result in (
                ExternalAccountingFailureKind.RETRYABLE,
                ExternalAccountingFailureKind.CONFIGURATION,
                ExternalAccountingFailureKind.CREDENTIAL,
            ):
                service.mark_failed(
                    record.id,
                    lease_token=claim.lease_token,
                    error_code=result.value,
                    error_message=result.value,
                )
                outcome = result.value
            else:
                result = ExternalAccountingFailureKind(result)
                terminal = replace(
                    record,
                    status=OutboxDeliveryStatus.DEAD_LETTER,
                    lease_token=None,
                    lease_expires_at=None,
                    last_error_code=result.value,
                    last_error_message=result.value,
                    updated_at=now,
                    row_version=record.row_version + 1,
                )
                repository.update(terminal, expected_row_version=record.row_version)
                outcome = result.value
            audit_repo = self._repository(SqlAlchemyAuditRepository, session)
            uow.record_event(
                AccountingTransportFinalized(
                    tenant_id=self._scope.tenant_id,
                    organization_id=self._scope.organization_id,
                    project_id=self._scope.project_id,
                    handoff_id=claim.evidence.handoff_id,
                    result="transport_accepted"
                    if isinstance(result, ExternalAccountingReceipt)
                    else result,
                    occurred_at=now,
                )
            )
            EnterpriseAuditService(
                session, audit_repo, tenant_context_service=self._scope
            ).record(
                operation="accounting_transport.finalize",
                entity_type="AccountingHandoff",
                entity_id=claim.evidence.handoff_id,
                entity_parent_id=self._scope.project_id,
                module="project_management",
                category="FINANCIAL",
                actor_id=actor_id,
                actor_type="service",
                source="ACCOUNTING_WORKER",
                project_id=self._scope.project_id,
                correlation_id=claim.evidence.correlation_id,
                commit=False,
                after_data={
                    "outcome": outcome,
                    "attempt": claim.attempt_count,
                    "approved_version": claim.evidence.source_version,
                },
            )
            uow.commit()
