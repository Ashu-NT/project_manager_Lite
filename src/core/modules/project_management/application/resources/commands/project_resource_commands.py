from __future__ import annotations

from src.core.modules.project_management.contracts.repositories.project import ProjectResourceRepository
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.domain.projects.project import ProjectResource
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.notifications.domain_events import domain_events

DEFAULT_CURRENCY_CODE = "EUR"


class ProjectResourceCommandMixin:
    _project_resource_repo: ProjectResourceRepository
    _resource_repo: ResourceRepository

    def add_to_project(
        self,
        project_id: str,
        resource_id: str,
        hourly_rate: float | None = None,
        currency_code: str | None = None,
        planned_hours: float = 0.0,
        is_active: bool = True,
    ) -> ProjectResource:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="add project resource",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "project.manage",
            operation_label="add project resource",
        )

        resource = self._resource_repo.get(resource_id)
        if not resource:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        if not resource.is_active:
            raise BusinessRuleError(
                "Inactive resource cannot be added to a project.",
                code="RESOURCE_INACTIVE",
            )

        existing = self._project_resource_repo.get_for_project(project_id, resource_id)
        if existing:
            raise BusinessRuleError(
                "Resource is already added to this project.",
                code="PROJECT_RESOURCE_EXISTS",
            )
        if planned_hours < 0:
            raise BusinessRuleError(
                "planned_hours cannot be negative.",
                code="PROJECT_RESOURCE_PLANNED_HOURS_INVALID",
            )

        resolved_currency = (currency_code or getattr(resource, "currency_code", None) or "").strip().upper()
        if not resolved_currency:
            resolved_currency = DEFAULT_CURRENCY_CODE

        project_resource = ProjectResource.create(
            project_id=project_id,
            resource_id=resource_id,
            hourly_rate=hourly_rate,
            currency_code=resolved_currency,
            planned_hours=planned_hours,
            is_active=is_active,
        )

        try:
            self._project_resource_repo.add(project_resource)
            self._session.commit()
            record_audit(
                self,
                action="project_resource.add",
                entity_type="project_resource",
                entity_id=project_resource.id,
                project_id=project_id,
                details={
                    "resource_name": resource.name,
                    "planned_hours": project_resource.planned_hours,
                    "hourly_rate": project_resource.hourly_rate,
                    "currency_code": project_resource.currency_code,
                    "is_active": project_resource.is_active,
                },
            )
        except Exception:
            self._session.rollback()
            raise

        domain_events.project_changed.emit(project_id)
        return project_resource

    def update(
        self,
        pr_id: str,
        hourly_rate: float | None,
        currency_code: str | None,
        planned_hours: float,
        is_active: bool,
    ) -> None:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="update project resource",
        )
        project_resource = self._project_resource_repo.get(pr_id)
        if not project_resource:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            project_resource.project_id,
            "project.manage",
            operation_label="update project resource",
        )
        if planned_hours < 0:
            raise BusinessRuleError(
                "planned_hours cannot be negative.",
                code="PROJECT_RESOURCE_PLANNED_HOURS_INVALID",
            )

        resolved_currency = (currency_code or "").strip().upper() or DEFAULT_CURRENCY_CODE
        project_resource.hourly_rate = hourly_rate
        project_resource.currency_code = resolved_currency
        project_resource.planned_hours = planned_hours
        project_resource.is_active = is_active
        resource = self._resource_repo.get(project_resource.resource_id)

        try:
            self._project_resource_repo.update(project_resource)
            self._session.commit()
            record_audit(
                self,
                action="project_resource.update",
                entity_type="project_resource",
                entity_id=project_resource.id,
                project_id=project_resource.project_id,
                details={
                    "resource_name": resource.name if resource is not None else project_resource.resource_id,
                    "planned_hours": project_resource.planned_hours,
                    "hourly_rate": project_resource.hourly_rate,
                    "currency_code": project_resource.currency_code,
                    "is_active": project_resource.is_active,
                },
            )
        except Exception:
            self._session.rollback()
            raise

        domain_events.project_changed.emit(project_resource.project_id)

    def set_active(self, pr_id: str, is_active: bool) -> None:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="toggle project resource active",
        )
        project_resource = self._project_resource_repo.get(pr_id)
        if not project_resource:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            project_resource.project_id,
            "project.manage",
            operation_label="toggle project resource active",
        )

        project_resource.is_active = is_active
        try:
            self._project_resource_repo.update(project_resource)
            self._session.commit()
            resource = self._resource_repo.get(project_resource.resource_id)
            record_audit(
                self,
                action="project_resource.set_active",
                entity_type="project_resource",
                entity_id=project_resource.id,
                project_id=project_resource.project_id,
                details={
                    "resource_name": resource.name if resource is not None else project_resource.resource_id,
                    "is_active": project_resource.is_active,
                },
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.project_changed.emit(project_resource.project_id)

    def delete(self, pr_id: str) -> None:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="delete project resource",
        )
        project_resource = self._project_resource_repo.get(pr_id)
        if not project_resource:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            project_resource.project_id,
            "project.manage",
            operation_label="delete project resource",
        )
        resource = self._resource_repo.get(project_resource.resource_id)
        try:
            self._project_resource_repo.delete(pr_id)
            self._session.commit()
            record_audit(
                self,
                action="project_resource.delete",
                entity_type="project_resource",
                entity_id=project_resource.id,
                project_id=project_resource.project_id,
                details={
                    "resource_name": resource.name if resource is not None else project_resource.resource_id,
                },
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.project_changed.emit(project_resource.project_id)


__all__ = ["DEFAULT_CURRENCY_CODE", "ProjectResourceCommandMixin"]
