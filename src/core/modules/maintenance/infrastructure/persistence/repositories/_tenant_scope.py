from __future__ import annotations

from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantParentScopedRepositorySupport,
    TenantScopedRepositorySupport,
)


class MaintenanceTenantScopedRepositorySupport(TenantScopedRepositorySupport):
    _repository_label = "Maintenance repository"


class MaintenanceParentScopedRepositorySupport(TenantParentScopedRepositorySupport):
    _repository_label = "Maintenance repository"


__all__ = [
    "MaintenanceParentScopedRepositorySupport",
    "MaintenanceTenantScopedRepositorySupport",
]
