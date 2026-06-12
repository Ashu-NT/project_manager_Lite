from __future__ import annotations

from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.platform.common.exceptions import ValidationError


class ProjectValidationMixin:
    _project_repo: ProjectRepository

    def _validate_project_name(
        self,
        name: str,
        *,
        organization_id: str,
        exclude_id: str | None = None,
    ) -> None:
        if not name or not name.strip():
            raise ValidationError("Project name cannot be empty.", code="PROJECT_NAME_EMPTY")
        if len(name.strip()) < 3:
            raise ValidationError("Project name must be at least 3 characters.", code="PROJECT_NAME_TOO_SHORT")

        for project in self._project_repo.list_for_organization(organization_id):
            if exclude_id is not None and project.id == exclude_id:
                continue
            if project.name.strip().lower() == name.strip().lower():
                raise ValidationError("A project with this name already exists.", code="PROJECT_NAME_DUPLICATE")


__all__ = ["ProjectValidationMixin"]
