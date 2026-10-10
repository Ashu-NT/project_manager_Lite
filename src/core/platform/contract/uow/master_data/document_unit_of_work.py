from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.master_data.documents.contracts import (
    DocumentLinkRepository,
    DocumentRepository,
    DocumentStructureRepository,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class DocumentUnitOfWork(UnitOfWork, Protocol):
    documents: DocumentRepository
    structures: DocumentStructureRepository
    links: DocumentLinkRepository
    _enterprise_audit_service: EnterpriseAuditService


class DocumentUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> DocumentUnitOfWork: ...  # type: ignore[override]


__all__ = ["DocumentUnitOfWork", "DocumentUnitOfWorkFactory"]
