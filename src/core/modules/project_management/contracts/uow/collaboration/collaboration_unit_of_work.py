from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.repositories.collaboration.collaboration import (
    TaskCommentRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class CollaborationUnitOfWork(UnitOfWork, Protocol):

    comments: TaskCommentRepository
    _enterprise_audit_service: EnterpriseAuditService


class CollaborationUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> CollaborationUnitOfWork: ...  # type: ignore[override]


__all__ = ["CollaborationUnitOfWork", "CollaborationUnitOfWorkFactory"]
