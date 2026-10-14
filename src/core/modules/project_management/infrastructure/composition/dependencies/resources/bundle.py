from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.resources.commands.project_resource_commands import (
    ProjectResourceCommandHandler,
)
from src.core.modules.project_management.application.resources.commands.resource_commands import (
    ResourceMasterCommandHandler,
)
from src.core.modules.project_management.application.resources.commands.skill_commands import (
    ResourceCapabilityCommandHandler,
)
from src.core.modules.project_management.application.resources.queries.project_resource_queries import (
    ProjectResourceQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.resource_context_queries import (
    ResourceContextQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.resource_queries import (
    ResourceQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.skill_queries import (
    ResourceCapabilityQueryHandler,
)


@dataclass(frozen=True)
class ResourceComposition:
    query: ResourceQueryHandler
    master_commands: ResourceMasterCommandHandler
    capability_commands: ResourceCapabilityCommandHandler
    capability_query: ResourceCapabilityQueryHandler
    context_query: ResourceContextQueryHandler


@dataclass(frozen=True)
class ProjectResourceComposition:
    commands: ProjectResourceCommandHandler
    query: ProjectResourceQueryHandler
