"""Collect explicit tenant administration handlers from a dynamic test graph."""

from src.core.platform.infrastructure.composition.dependencies.tenancy.admin import (
    TenantAdminDependencies,
)


def tenant_admin_operations(services) -> TenantAdminDependencies:
    return TenantAdminDependencies(
        tenant_admin_queries=services["tenant_admin_queries"],
        tenant_lifecycle_commands=services["tenant_lifecycle_commands"],
    )
