from __future__ import annotations

from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)


class InventoryTenantScopedRepositorySupport(TenantScopedRepositorySupport):
    _repository_label = "Inventory repository"


__all__ = ["InventoryTenantScopedRepositorySupport"]
