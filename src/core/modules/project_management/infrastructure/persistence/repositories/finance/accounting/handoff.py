from sqlalchemy import select

from src.core.modules.project_management.domain.financials.accounting.handoff import AccountingHandoffSnapshot
from src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff import ProjectAccountingHandoffORM, ProjectAccountingOutboxORM
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import TenantScopedRepositorySupport
from src.infra.persistence.repositories.integration_delivery import SqlAlchemyIntegrationOutboxRepository


class SqlAlchemyAccountingHandoffRepository(TenantScopedRepositorySupport):
    _repository_label = "PM Accounting handoff"

    def __init__(self, session):
        self.session = session
        self._tenant_context_service = None

    def get_for_preparation(self, project_id, preparation_id):
        scope = self._context(operation_label="read PM handoff")
        row = self.session.execute(select(ProjectAccountingHandoffORM).where(
            ProjectAccountingHandoffORM.tenant_id == scope.tenant_id,
            ProjectAccountingHandoffORM.organization_id == scope.organization_id,
            ProjectAccountingHandoffORM.project_id == project_id,
            ProjectAccountingHandoffORM.preparation_id == preparation_id,
        )).scalar_one_or_none()
        if row is None:
            return None
        snapshot = AccountingHandoffSnapshot.model_validate_json(row.payload_bytes)
        evidence = snapshot.evidence
        if (snapshot.content_hash != row.payload_hash or snapshot.canonical_bytes != row.payload_bytes
                or (snapshot.handoff_id, evidence.tenant_id, evidence.organization_id, evidence.project_id, evidence.preparation_id, snapshot.approved_preparation_version)
                != (row.id, row.tenant_id, row.organization_id, row.project_id, row.preparation_id, row.approved_version)):
            raise BusinessRuleError("Handoff integrity check failed.", code="ACCOUNTING_HANDOFF_INTEGRITY_FAILED")
        return snapshot

    def add(self, snapshot):
        scope = self._context(operation_label="persist PM handoff")
        evidence = snapshot.evidence
        if (evidence.tenant_id, evidence.organization_id) != (scope.tenant_id, scope.organization_id):
            raise BusinessRuleError("Handoff scope mismatch.", code="INTEGRATION_SCOPE_VIOLATION")
        existing = self.get_for_preparation(evidence.project_id, evidence.preparation_id)
        if existing is not None:
            if existing.content_hash != snapshot.content_hash:
                raise BusinessRuleError("Handoff immutable content conflict.", code="ACCOUNTING_HANDOFF_CONTENT_CONFLICT")
            return
        self.session.add(ProjectAccountingHandoffORM(
            id=snapshot.handoff_id, tenant_id=evidence.tenant_id,
            organization_id=evidence.organization_id, project_id=evidence.project_id,
            preparation_id=evidence.preparation_id, approved_version=snapshot.approved_preparation_version,
            handoff_kind="billing_preparation", payload_bytes=snapshot.canonical_bytes,
            payload_hash=snapshot.content_hash,
        ))
        self.session.flush()


class SqlAlchemyAccountingOutboxRepository(SqlAlchemyIntegrationOutboxRepository):
    def __init__(self, session):
        super().__init__(session, orm_type=ProjectAccountingOutboxORM, owner_module="project_management")

    def _additional_insert_values(self, record):
        return {"project_id": record.envelope.payload["evidence"]["project_id"]}
