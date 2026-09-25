from sqlalchemy import select, update

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.integration.accounting.connector import AccountingConnectorConfiguration
from src.core.platform.infrastructure.persistence.orm.integration.accounting_connector import AccountingConnectorORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import TenantScopedRepositorySupport


class SqlAlchemyAccountingConnectorRepository(TenantScopedRepositorySupport):
    _repository_label = "Accounting connector"

    def __init__(self, session):
        self.session = session
        self._tenant_context_service = None

    def get(self, *, for_update=False):
        scope = self._context(operation_label="read Accounting connector")
        statement = select(AccountingConnectorORM).where(
            AccountingConnectorORM.tenant_id == scope.tenant_id,
            AccountingConnectorORM.organization_id == scope.organization_id,
        ).execution_options(populate_existing=True)
        if for_update:
            statement = statement.with_for_update()
        row = self.session.execute(statement).scalar_one_or_none()
        return AccountingConnectorConfiguration.model_validate({
            key: getattr(row, key) for key in AccountingConnectorConfiguration.model_fields
        }) if row else None

    def save(self, configuration, *, expected_version):
        scope = self._context(operation_label="configure Accounting connector")
        if (configuration.tenant_id, configuration.organization_id) != (scope.tenant_id, scope.organization_id):
            raise BusinessRuleError("Connector scope mismatch.", code="INTEGRATION_SCOPE_VIOLATION")
        values = configuration.model_dump()
        if expected_version is None:
            if configuration.version != 1:
                raise BusinessRuleError("Invalid connector version.", code="STALE_WRITE")
            self.session.add(AccountingConnectorORM(**values))
        else:
            if configuration.version != expected_version + 1:
                raise BusinessRuleError("Invalid connector version.", code="STALE_WRITE")
            result = self.session.execute(update(AccountingConnectorORM).where(
                AccountingConnectorORM.tenant_id == scope.tenant_id,
                AccountingConnectorORM.organization_id == scope.organization_id,
                AccountingConnectorORM.version == expected_version,
            ).values(**values))
            if result.rowcount != 1:
                raise BusinessRuleError("Connector changed concurrently.", code="STALE_WRITE")
        self.session.flush()
