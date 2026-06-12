"""Maintenance desktop runtime composition."""

from src.core.modules.maintenance.api.desktop_runtime.desktop_api_builder import (
    build_maintenance_desktop_runtime_apis,
)
from src.core.modules.maintenance.api.desktop_runtime.registry import (
    MaintenanceDesktopRuntimeApis,
    MaintenanceDesktopRuntimePlatformDependencies,
)

__all__ = [
    "MaintenanceDesktopRuntimeApis",
    "MaintenanceDesktopRuntimePlatformDependencies",
    "build_maintenance_desktop_runtime_apis",
]
