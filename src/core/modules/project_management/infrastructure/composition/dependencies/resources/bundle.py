from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.resources.catalog.resource_service import (
    ResourceService,
)
from src.core.modules.project_management.application.resources.queries.resource_context_queries import (
    ResourceContextQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.skill_queries import (
    ResourceCapabilityQueryHandler,
)


@dataclass(frozen=True)
class ResourceComposition:
    service: ResourceService
    capability_query: ResourceCapabilityQueryHandler
    context_query: ResourceContextQueryHandler
