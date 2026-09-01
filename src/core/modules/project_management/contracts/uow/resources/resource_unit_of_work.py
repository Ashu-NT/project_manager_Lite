from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.skills import (
    ResourceCertificationRepository,
    ResourceSkillRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class ResourceUnitOfWork(UnitOfWork, Protocol):
    """One fresh transaction for Resource Master and Resource Capability (skill/certification)
    mutations. Both sub-aggregates share one UoW -- exactly like DocumentUnitOfWork's
    documents/structures/links -- because they are one business capability, even though no
    single operation currently writes to more than one of these repositories at once."""

    resources: ResourceRepository
    skills: ResourceSkillRepository
    certifications: ResourceCertificationRepository
    _enterprise_audit_service: EnterpriseAuditService


class ResourceUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> ResourceUnitOfWork: ...  # type: ignore[override]


__all__ = ["ResourceUnitOfWork", "ResourceUnitOfWorkFactory"]
