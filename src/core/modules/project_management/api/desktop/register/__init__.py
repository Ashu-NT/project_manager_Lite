"""Register desktop API package."""

from src.core.modules.project_management.api.desktop.register.api import (
    ProjectManagementRegisterDesktopApi,
)
from src.core.modules.project_management.api.desktop.register.commands.entry_commands import (
    RegisterEntryCreateCommand,
    RegisterEntryUpdateCommand,
)
from src.core.modules.project_management.api.desktop.register.factories.register_api_factory import (
    build_project_management_register_desktop_api,
)
from src.core.modules.project_management.api.desktop.register.models.entries import (
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
    "RegisterEntryCreateCommand",
    "RegisterEntryDesktopDto",
    "RegisterEntrySeverityDescriptor",
    "RegisterEntryStatusDescriptor",
    "RegisterEntryTypeDescriptor",
    "RegisterEntryUpdateCommand",
    "RegisterProjectOptionDescriptor",
    "build_project_management_register_desktop_api",
]
