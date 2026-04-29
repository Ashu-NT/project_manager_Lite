"""Resource queries."""

from src.core.modules.project_management.application.resources.queries.project_resource_queries import (
    ProjectResourceQueryMixin,
)
from src.core.modules.project_management.application.resources.queries.resource_queries import (
    ResourceQueryMixin,
)

__all__ = ["ProjectResourceQueryMixin", "ResourceQueryMixin"]
