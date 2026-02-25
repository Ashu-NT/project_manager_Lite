# core/services/project_resource_service.py
from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session


from core.models import ProjectResource
from core.exceptions import BusinessRuleError, NotFoundError
from core.interfaces import (
    ProjectResourceRepository,
    ResourceRepository,
)
from core.events.domain_events import domain_events
from core.services.audit.helpers import record_audit
from core.services.auth.authorization import require_permission

DEFAULT_CURRENCY_CODE = "EUR"


class ProjectResourceService:
    """
    Manages project-specific resource membership and overrides.
    This is the planning layer between Resource (master data)
    and TaskAssignment (execution).
    """

    def __init__(
        self,
        project_resource_repo: ProjectResourceRepository,
        resource_repo: ResourceRepository,
        session: Session,
        user_session=None,
        audit_service=None,
    ):
        self._project_resource_repo: ProjectResourceRepository = project_resource_repo
        self._resource_repo: ResourceRepository = resource_repo
        self._session: Session = session
        self._user_session = user_session
        self._audit_service = audit_service

    # -------------------------
    # Query methods
    # -------------------------
    def list_by_project(self, project_id: str) -> List[ProjectResource]:
        return self._project_resource_repo.list_by_project(project_id)

    def get(self, project_resource_id: str) -> Optional[ProjectResource]:
        return self._project_resource_repo.get(project_resource_id)

    def get_for_project(self, project_id: str, resource_id: str) -> Optional[ProjectResource]:
        return self._project_resource_repo.get_for_project(project_id, resource_id)

    # -------------------------
    # Commands
    # -------------------------
    def add_to_project(
        self,
        project_id: str,
        resource_id: str,
        hourly_rate: Optional[float] = None,
        currency_code: Optional[str] = None,
        planned_hours: float = 0.0,
        is_active: bool = True,
    ) -> ProjectResource:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="add project resource",
        )
        # Validate resource exists
        res = self._resource_repo.get(resource_id)
        if not res:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")

        # Enforce global resource active rule
        if not res.is_active:
            raise BusinessRuleError(
                "Inactive resource cannot be added to a project.",
                code="RESOURCE_INACTIVE",
            )

        # Prevent duplicates
        existing = self._project_resource_repo.get_for_project(project_id, resource_id)
        if existing:
            raise BusinessRuleError(
                "Resource is already added to this project.",
                code="PROJECT_RESOURCE_EXISTS",
            )

        if planned_hours < 0:
            raise BusinessRuleError("planned_hours cannot be negative.", code="PROJECT_RESOURCE_PLANNED_HOURS_INVALID")

        resolved_currency = (currency_code or getattr(res, "currency_code", None) or "").strip().upper()
        if not resolved_currency:
            resolved_currency = DEFAULT_CURRENCY_CODE

        pr = ProjectResource.create(
            project_id=project_id,
            resource_id=resource_id,
            hourly_rate=hourly_rate,
            currency_code=resolved_currency,
            planned_hours=planned_hours,
            is_active=is_active,
        )

        try:
            self._project_resource_repo.add(pr)
            self._session.commit()
            record_audit(
                self,
                action="project_resource.add",
                entity_type="project_resource",
                entity_id=pr.id,
                project_id=project_id,
                details={
                    "resource_name": res.name,
                    "planned_hours": pr.planned_hours,
                    "hourly_rate": pr.hourly_rate,
                    "currency_code": pr.currency_code,
                    "is_active": pr.is_active,
                },
            )
        except Exception:
            self._session.rollback()
            raise
        
        domain_events.project_changed.emit(project_id)
        return pr

    def update(
        self,
        pr_id: str,
        hourly_rate: Optional[float],
        currency_code: Optional[str],
        planned_hours: float,
        is_active: bool,
    ) -> None:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="update project resource",
        )
        pr = self._project_resource_repo.get(pr_id)
        if not pr:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")

        if planned_hours < 0:
            raise BusinessRuleError("planned_hours cannot be negative.", code="PROJECT_RESOURCE_PLANNED_HOURS_INVALID")

        resolved_currency = (currency_code or "").strip().upper() or DEFAULT_CURRENCY_CODE
        pr.hourly_rate = hourly_rate
        pr.currency_code = resolved_currency
        pr.planned_hours = planned_hours
        pr.is_active = is_active
        resource = self._resource_repo.get(pr.resource_id)

        try:
            # repo holds ORM, so flush is enough
            self._project_resource_repo.update(pr)
            self._session.commit()
            record_audit(
                self,
                action="project_resource.update",
                entity_type="project_resource",
                entity_id=pr.id,
                project_id=pr.project_id,
                details={
                    "resource_name": resource.name if resource is not None else pr.resource_id,
                    "planned_hours": pr.planned_hours,
                    "hourly_rate": pr.hourly_rate,
                    "currency_code": pr.currency_code,
                    "is_active": pr.is_active,
                },
            )
        except Exception:
            self._session.rollback()
            raise
        
        domain_events.project_changed.emit(pr.project_id)

    def set_active(self, pr_id: str, is_active: bool) -> None:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="toggle project resource active",
        )
        pr = self._project_resource_repo.get(pr_id)
        if not pr:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")

        pr.is_active = is_active
        try:
            self._project_resource_repo.update(pr)
            self._session.commit()
            resource = self._resource_repo.get(pr.resource_id)
            record_audit(
                self,
                action="project_resource.set_active",
                entity_type="project_resource",
                entity_id=pr.id,
                project_id=pr.project_id,
                details={
                    "resource_name": resource.name if resource is not None else pr.resource_id,
                    "is_active": pr.is_active,
                },
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.project_changed.emit(pr.project_id)

    def delete(self, pr_id: str) -> None:
        require_permission(
            self._user_session,
            "project.manage",
            operation_label="delete project resource",
        )
        pr = self._project_resource_repo.get(pr_id)
        if not pr:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")
        resource = self._resource_repo.get(pr.resource_id)
        try:
            self._project_resource_repo.delete(pr_id)
            self._session.commit()
            record_audit(
                self,
                action="project_resource.delete",
                entity_type="project_resource",
                entity_id=pr.id,
                project_id=pr.project_id,
                details={
                    "resource_name": resource.name if resource is not None else pr.resource_id,
                },
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.project_changed.emit(pr.project_id)
    


