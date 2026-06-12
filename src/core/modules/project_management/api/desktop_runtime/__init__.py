"""Project management desktop runtime composition."""

from src.core.modules.project_management.api.desktop_runtime.desktop_api_builder import (
    build_project_management_desktop_runtime_apis,
)
from src.core.modules.project_management.api.desktop_runtime.registry import (
    ProjectManagementDesktopRuntimeApis,
    ProjectManagementDesktopRuntimePlatformDependencies,
)

__all__ = [
    "ProjectManagementDesktopRuntimeApis",
    "ProjectManagementDesktopRuntimePlatformDependencies",
    "build_project_management_desktop_runtime_apis",
]
