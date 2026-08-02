from __future__ import annotations

from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantParentScopedRepositorySupport,
    TenantScopedRepositorySupport,
)


class ProjectManagementTenantScopedRepositorySupport(TenantScopedRepositorySupport):
    _repository_label = "Project management repository"


class ProjectManagementParentScopedRepositorySupport(
    TenantParentScopedRepositorySupport
):
    _repository_label = "Project management repository"


__all__ = [
    "ProjectManagementParentScopedRepositorySupport",
    "ProjectManagementTenantScopedRepositorySupport",
]
