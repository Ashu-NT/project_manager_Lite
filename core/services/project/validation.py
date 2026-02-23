from __future__ import annotations

from core.exceptions import ValidationError
from core.interfaces import ProjectRepository


class ProjectValidationMixin:
    _project_repo: ProjectRepository

    def _validate_project_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("Project name cannot be empty.", code="PROJECT_NAME_EMPTY")
        if len(name.strip()) < 3:
            raise ValidationError("Project name must be at least 3 characters.", code="PROJECT_NAME_TOO_SHORT")

        for project in self._project_repo.list_all():
            if project.name.strip().lower() == name.strip().lower():
                raise ValidationError("A project with this name already exists.", code="PROJECT_NAME_DUPLICATE")


__all__ = ["ProjectValidationMixin"]
