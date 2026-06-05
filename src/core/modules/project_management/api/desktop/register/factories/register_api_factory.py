from __future__ import annotations

from src.core.modules.project_management.api.desktop.register.api import (
    ProjectManagementRegisterDesktopApi,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.risk import RegisterService


def build_project_management_register_desktop_api(
    *,
    project_service: ProjectService | None = None,
    register_service: RegisterService | None = None,
) -> ProjectManagementRegisterDesktopApi:
    return ProjectManagementRegisterDesktopApi(
        project_service=project_service,
        register_service=register_service,
    )


__all__ = ["build_project_management_register_desktop_api"]
