from __future__ import annotations

from collections.abc import Mapping

from src.core.platform.application.tenant.modules import ModuleCatalogService


def resolve_module_catalog_service(
    services: Mapping[str, object],
) -> ModuleCatalogService | None:
    candidate = services.get("module_catalog_service")
    return candidate if isinstance(candidate, ModuleCatalogService) else None


__all__ = [
    "resolve_module_catalog_service",
]
