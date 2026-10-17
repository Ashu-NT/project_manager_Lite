"""Scheduling desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.modules.project_management.api.desktop.scheduling.factories.scheduling_api_factory import (
    build_project_management_scheduling_desktop_api,
)
from src.core.modules.project_management.api.desktop.scheduling.models import (
    SchedulingDependencyTypeDescriptor,
    SchedulingProjectOptionDescriptor,
)

__all__ = ['ProjectManagementSchedulingDesktopApi', 'SchedulingDependencyTypeDescriptor', 'SchedulingProjectOptionDescriptor', 'build_project_management_scheduling_desktop_api']
