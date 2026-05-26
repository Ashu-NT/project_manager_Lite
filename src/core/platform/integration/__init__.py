from __future__ import annotations

from src.core.platform.integration.cross_module_reference import (
    CrossModuleReference,
    ResolvedReference,
)
from src.core.platform.integration.module_registry import ModuleRegistry
from src.core.platform.integration.resolver import IntegrationResolver

__all__ = [
    "CrossModuleReference",
    "IntegrationResolver",
    "ModuleRegistry",
    "ResolvedReference",
]
