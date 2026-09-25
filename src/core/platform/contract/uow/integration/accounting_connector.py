from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService
from src.core.platform.contract.repositories.integration.accounting_connector import AccountingConnectorRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class AccountingConnectorUnitOfWork(UnitOfWork, Protocol):
    accounting_connectors: AccountingConnectorRepository
    _enterprise_audit_service: EnterpriseAuditService


class AccountingConnectorUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> AccountingConnectorUnitOfWork: ...
