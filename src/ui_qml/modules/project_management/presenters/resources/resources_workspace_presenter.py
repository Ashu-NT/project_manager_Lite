from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
    build_project_management_resources_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceAvailabilityViewModel,
    ResourceCatalogWorkspaceViewModel,
    ResourceCertificationViewModel,
    ResourceSkillViewModel,
)

from .assignments_builder import build_resource_assignments
from .certifications_builder import (
    add_certification,
    build_certifications_state,
    remove_certification,
)
from .command_handler import (
    create_resource,
    delete_resource,
    suggest_code,
    toggle_resource_active,
    update_resource,
)
from .skills_builder import add_skill, build_skills_state, remove_skill
from .workspace_builder import build_workspace_state


class ProjectResourcesWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementResourcesDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_resources_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        active_filter: str = "all",
        category_filter: str = "all",
        selected_resource_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> ResourceCatalogWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            search_text=search_text,
            active_filter=active_filter,
            category_filter=category_filter,
            selected_resource_id=selected_resource_id,
            page=page,
            page_size=page_size,
        )

    def suggest_code(self, payload: dict[str, Any]) -> str:
        return suggest_code(self._desktop_api, payload)

    def create_resource(self, payload: dict[str, Any]) -> None:
        create_resource(self._desktop_api, payload)

    def update_resource(self, payload: dict[str, Any]) -> None:
        update_resource(self._desktop_api, payload)

    def toggle_resource_active(
        self,
        resource_id: str,
        expected_version: int | None = None,
    ) -> None:
        toggle_resource_active(self._desktop_api, resource_id, expected_version)

    def delete_resource(self, resource_id: str) -> None:
        delete_resource(self._desktop_api, resource_id)

    def build_resource_assignments(self, resource_id: str) -> list[dict[str, object]]:
        return build_resource_assignments(self._desktop_api, resource_id)

    def build_skills_state(self, resource_id: str) -> tuple[ResourceSkillViewModel, ...]:
        return build_skills_state(self._desktop_api, resource_id)

    def build_certifications_state(
        self, resource_id: str
    ) -> tuple[ResourceCertificationViewModel, ...]:
        return build_certifications_state(self._desktop_api, resource_id)

    def add_skill(self, resource_id: str, payload: dict[str, Any]) -> None:
        add_skill(self._desktop_api, resource_id, payload)

    def remove_skill(self, skill_id: str) -> None:
        remove_skill(self._desktop_api, skill_id)

    def add_certification(self, resource_id: str, payload: dict[str, Any]) -> None:
        add_certification(self._desktop_api, resource_id, payload)

    def remove_certification(self, cert_id: str) -> None:
        remove_certification(self._desktop_api, cert_id)


__all__ = ["ProjectResourcesWorkspacePresenter"]
