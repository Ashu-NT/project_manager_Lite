"""Resources desktop API package."""

from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.api.desktop.resources.commands.certification_commands import (
    ResourceAddCertificationCommand,
)
from src.core.modules.project_management.api.desktop.resources.commands.resource_commands import (
    ResourceCreateCommand,
    ResourceLifecycleCommand,
    ResourcePurgeCommand,
    ResourceUpdateCommand,
)
from src.core.modules.project_management.api.desktop.resources.commands.skill_commands import (
    ResourceAddSkillCommand,
)
from src.core.modules.project_management.api.desktop.resources.factories.resources_api_factory import (
    build_project_management_resources_desktop_api,
)
from src.core.modules.project_management.api.desktop.resources.models.assignments import (
    ResourceAssignmentDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.models.availability import (
    ResourceAvailabilityDayDto,
    ResourceAvailabilityDto,
)
from src.core.modules.project_management.api.desktop.resources.models.certifications import (
    ResourceCertificationDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.models.options import (
    ResourceCategoryDescriptor,
    ResourceEmployeeOptionDescriptor,
    ResourceKindDescriptor,
    ResourceScopeOptionDescriptor,
    ResourceWorkerTypeDescriptor,
)
from src.core.modules.project_management.api.desktop.resources.models.resources import (
    ResourceCatalogItemDesktopDto,
    ResourceCatalogPageDesktopDto,
    ResourceDesktopDto,
    ResourceInspectorDesktopDto,
    ResourceSummaryDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.models.skills import (
    ResourceSkillDesktopDto,
)

__all__ = [
    "ProjectManagementResourcesDesktopApi",
    "ResourceAddCertificationCommand",
    "ResourceAddSkillCommand",
    "ResourceAssignmentDesktopDto",
    "ResourceAvailabilityDayDto",
    "ResourceAvailabilityDto",
    "ResourceCategoryDescriptor",
    "ResourceCatalogItemDesktopDto",
    "ResourceCatalogPageDesktopDto",
    "ResourceCertificationDesktopDto",
    "ResourceCreateCommand",
    "ResourceDesktopDto",
    "ResourceEmployeeOptionDescriptor",
    "ResourceInspectorDesktopDto",
    "ResourceKindDescriptor",
    "ResourceLifecycleCommand",
    "ResourcePurgeCommand",
    "ResourceScopeOptionDescriptor",
    "ResourceSkillDesktopDto",
    "ResourceUpdateCommand",
    "ResourceSummaryDesktopDto",
    "ResourceWorkerTypeDescriptor",
    "build_project_management_resources_desktop_api",
]
