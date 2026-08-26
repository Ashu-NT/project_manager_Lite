"""Resources desktop API package."""

from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.api.desktop.resources.commands.certification_commands import (
    ResourceAddCertificationCommand,
    ResourceRemoveCertificationCommand,
    ResourceUpdateCertificationCommand,
)
from src.core.modules.project_management.api.desktop.resources.commands.resource_commands import (
    ResourceCreateCommand,
    ResourceLifecycleCommand,
    ResourcePurgeCommand,
    ResourceUpdateCommand,
)
from src.core.modules.project_management.api.desktop.resources.commands.skill_commands import (
    ResourceAddSkillCommand,
    ResourceRemoveSkillCommand,
    ResourceUpdateSkillCommand,
)
from src.core.modules.project_management.api.desktop.resources.factories.resources_api_factory import (
    build_project_management_resources_desktop_api,
)
from src.core.modules.project_management.api.desktop.resources.models.context import (
    ResourceActivityDesktopDto,
    ResourceActivityPageDesktopDto,
    ResourceAssignmentDesktopDto,
    ResourceAssignmentsPageDesktopDto,
    ResourceProjectDesktopDto,
    ResourceProjectsPageDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.models.availability import (
    ResourceAvailabilityDayDto,
    ResourceAvailabilityDto,
)
from src.core.modules.project_management.api.desktop.resources.models.certifications import (
    ResourceCertificationDesktopDto,
    ResourceCertificationsPageDesktopDto,
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
    ResourceSkillsPageDesktopDto,
)

__all__ = [
    "ProjectManagementResourcesDesktopApi",
    "ResourceAddCertificationCommand",
    "ResourceAddSkillCommand",
    "ResourceRemoveCertificationCommand",
    "ResourceRemoveSkillCommand",
    "ResourceAssignmentDesktopDto",
    "ResourceAssignmentsPageDesktopDto",
    "ResourceActivityDesktopDto",
    "ResourceActivityPageDesktopDto",
    "ResourceAvailabilityDayDto",
    "ResourceAvailabilityDto",
    "ResourceCategoryDescriptor",
    "ResourceCatalogItemDesktopDto",
    "ResourceCatalogPageDesktopDto",
    "ResourceCertificationDesktopDto",
    "ResourceCertificationsPageDesktopDto",
    "ResourceCreateCommand",
    "ResourceDesktopDto",
    "ResourceEmployeeOptionDescriptor",
    "ResourceInspectorDesktopDto",
    "ResourceKindDescriptor",
    "ResourceLifecycleCommand",
    "ResourcePurgeCommand",
    "ResourceProjectDesktopDto",
    "ResourceProjectsPageDesktopDto",
    "ResourceScopeOptionDescriptor",
    "ResourceSkillDesktopDto",
    "ResourceSkillsPageDesktopDto",
    "ResourceUpdateCommand",
    "ResourceUpdateCertificationCommand",
    "ResourceUpdateSkillCommand",
    "ResourceSummaryDesktopDto",
    "ResourceWorkerTypeDescriptor",
    "build_project_management_resources_desktop_api",
]
