"""Register desktop API package."""

from src.core.modules.project_management.api.desktop.register.api import (
    ProjectManagementRegisterDesktopApi,
)
from src.core.modules.project_management.api.desktop.register.factories.register_api_factory import (
    build_project_management_register_desktop_api,
)
from src.core.modules.project_management.api.desktop.register.models.entries import (
    RegisterCatalogPageDesktopDto,
    RegisterEntryDesktopDto,
)
from src.core.modules.project_management.api.desktop.register.models.options import (
    RegisterEntrySeverityDescriptor,
    RegisterEntryStatusDescriptor,
    RegisterEntryTypeDescriptor,
    RegisterProjectOptionDescriptor,
)

__all__ = [
    "ProjectManagementRegisterDesktopApi",
    "RegisterCatalogPageDesktopDto",
    "RegisterEntryDesktopDto",
    "RegisterEntrySeverityDescriptor",
    "RegisterEntryStatusDescriptor",
    "RegisterEntryTypeDescriptor",
    "RegisterProjectOptionDescriptor",
    "build_project_management_register_desktop_api",
]
