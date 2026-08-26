from __future__ import annotations

from datetime import date
from typing import Protocol

from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.domain.enums import ProjectStatus, TaskStatus

from .models import (
    ResourceActivityReadPage,
    ResourceAssignmentReadPage,
    ResourceProjectReadPage,
    ResourceCertificationReadPage,
    ResourceSkillReadPage,
)


class ResourceProjectsReader(Protocol):
    def read_projects_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        search_text: str,
        active: bool | None,
        status: ProjectStatus | None,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> ResourceProjectReadPage: ...


class ResourceAssignmentsReader(Protocol):
    def read_assignments_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        search_text: str,
        project_id: str | None,
        task_status: TaskStatus | None,
        assignment_status: str | None,
        lifecycle: str,
        start_date: date | None,
        end_date: date | None,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> ResourceAssignmentReadPage: ...


class ResourceActivityReader(Protocol):
    def read_activity_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        allowed_task_project_ids: tuple[str, ...] | None,
        category: str,
        start_date: date | None,
        end_date: date | None,
        page: int,
        page_size: int,
    ) -> ResourceActivityReadPage: ...


class ResourceCapabilityReader(Protocol):
    def read_skills_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
        search_text: str,
        proficiency: str | None,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> ResourceSkillReadPage: ...

    def read_certifications_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
        search_text: str,
        status: str | None,
        as_of: date,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> ResourceCertificationReadPage: ...


__all__ = [
    "ResourceActivityReader",
    "ResourceAssignmentsReader",
    "ResourceCapabilityReader",
    "ResourceProjectsReader",
]
