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
    ResourceCapabilityCountsViewModel,
    ResourceSkillViewModel,
)

from .assignments_builder import build_resource_assignments
from .availability_builder import build_resource_availability_state
from .certifications_builder import (
    add_certification,
    build_certifications_state,
    remove_certification,
    update_certification,
)
from .command_handler import (
    create_resource,
    deactivate_resource,
    reactivate_resource,
    suggest_code,
    update_resource,
)
from .skills_builder import add_skill, build_skills_state, remove_skill, update_skill
from .workspace_builder import build_workspace_state
from .resource_mapper import to_resource_record_view_model
from .detail_builder import build_detail_view_model, build_inspector_view_model

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
        sort_key: str = "catalog",
        sort_direction: str = "asc",
    ) -> ResourceCatalogWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            search_text=search_text,
            active_filter=active_filter,
            category_filter=category_filter,
            selected_resource_id=selected_resource_id,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )

    def list_export_records(
        self,
        *,
        search_text: str = "",
        active_filter: str = "all",
        category_filter: str = "all",
        sort_key: str = "catalog",
        sort_direction: str = "asc",
        batch_size: int = 500,
    ) -> tuple:
        records = []
        page = 1
        while True:
            result = self._desktop_api.list_resource_page(
                search_text=search_text,
                active=active_filter,
                category=category_filter,
                page=page,
                page_size=batch_size,
                sort_key=sort_key,
                sort_direction=sort_direction,
            )
            records.extend(to_resource_record_view_model(item) for item in result.items)
            if page * result.page_size >= result.filtered_total:
                break
            page += 1
        return tuple(records)

    def build_resource_inspector(self, resource_id: str):
        return build_inspector_view_model(
            self._desktop_api.get_resource_inspector(resource_id)
        )

    def build_resource_detail(self, resource_id: str):
        return build_detail_view_model(
            self._desktop_api.get_resource_summary(resource_id)
        )

    def suggest_code(self, payload: dict[str, Any]) -> str:
        return suggest_code(self._desktop_api, payload)

    def create_resource(self, payload: dict[str, Any]) -> None:
        create_resource(self._desktop_api, payload)

    def update_resource(self, payload: dict[str, Any]) -> None:
        update_resource(self._desktop_api, payload)

    def deactivate_resource(
        self,
        resource_id: str,
        expected_version: int,
    ) -> None:
        deactivate_resource(self._desktop_api, resource_id, expected_version)

    def reactivate_resource(self, resource_id: str, expected_version: int) -> None:
        reactivate_resource(self._desktop_api, resource_id, expected_version)

    def build_resource_assignments(self, resource_id: str) -> list[dict[str, object]]:
        return build_resource_assignments(self._desktop_api, resource_id)

    def build_resource_availability(
        self, resource_id: str, *, start_date: str, end_date: str
    ) -> ResourceAvailabilityViewModel:
        return build_resource_availability_state(
            self._desktop_api,
            resource_id,
            start_date=start_date,
            end_date=end_date,
        )

    def build_skills_state(self, resource_id: str) -> tuple[ResourceSkillViewModel, ...]:
        return build_skills_state(self._desktop_api, resource_id)

    def build_capability_counts(
        self, resource_id: str
    ) -> ResourceCapabilityCountsViewModel:
        counts = self._desktop_api.get_resource_capability_counts(resource_id)
        return ResourceCapabilityCountsViewModel(
            skill_count=counts.skill_count,
            certification_count=counts.certification_count,
        )

    def build_certifications_state(
        self, resource_id: str
    ) -> tuple[ResourceCertificationViewModel, ...]:
        return build_certifications_state(self._desktop_api, resource_id)

    def add_skill(self, resource_id: str, payload: dict[str, Any]) -> None:
        add_skill(self._desktop_api, resource_id, payload)

    def update_skill(self, payload: dict[str, Any]) -> None:
        update_skill(self._desktop_api, payload)

    def remove_skill(self, skill_id: str, expected_version: int) -> None:
        remove_skill(self._desktop_api, skill_id, expected_version)

    def add_certification(self, resource_id: str, payload: dict[str, Any]) -> None:
        add_certification(self._desktop_api, resource_id, payload)

    def update_certification(self, payload: dict[str, Any]) -> None:
        update_certification(self._desktop_api, payload)

    def remove_certification(self, cert_id: str, expected_version: int) -> None:
        remove_certification(self._desktop_api, cert_id, expected_version)

__all__ = ["ProjectResourcesWorkspacePresenter"]
