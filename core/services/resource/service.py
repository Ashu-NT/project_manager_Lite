# core/services/resource_service.py
from __future__ import annotations
from typing import List
from sqlalchemy.orm import Session

from core.models import Resource, CostType
from core.interfaces import ResourceRepository, AssignmentRepository, ProjectResourceRepository
from core.exceptions import NotFoundError, ValidationError
import logging

logger = logging.getLogger(__name__)

class ResourceService:
    def __init__(self, session: Session, 
                 resource_repo: ResourceRepository, 
                 assignment_repo: AssignmentRepository,
                 project_resource_repo: ProjectResourceRepository | None = None
        ):
        self._session = session
        self._resource_repo = resource_repo
        self._assignment_repo = assignment_repo
        self._project_resource_repo = project_resource_repo

    def create_resource(
        self,
        name: str,
        role: str = "",
        hourly_rate: float = 0.0,
        is_active: bool = True,
        cost_type: CostType = CostType.LABOR,
        currency_code: str | None = None,
    ) -> Resource:
        if not name or not name.strip():
            raise ValidationError("Resource name cannot be empty.")
        resource = Resource.create(
            name=name.strip(),
            role=role.strip(),
            hourly_rate=hourly_rate,
            is_active=is_active,
            cost_type=cost_type,
            currency_code=currency_code,
        )
        try:
            self._resource_repo.add(resource)
            self._session.commit()
            logger.info(f"Created resource {resource.id} - {resource.name}")
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error creating resource: {e}")
            raise 
        return resource

    def update_resource(
        self,
        resource_id: str,
        name: str | None = None,
        role: str | None = None,
        hourly_rate: float | None = None,
        is_active: bool | None = None,
        cost_type: CostType | None = None,
        currency_code: str | None = None,
    ) -> Resource:
        resource = self._resource_repo.get(resource_id)
        if not resource:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")

        if name is not None:
            if not name.strip():
                raise ValidationError("Resource name cannot be empty.")
            resource.name = name.strip()
        if role is not None:
            resource.role = role.strip()
        if hourly_rate is not None:
            if hourly_rate < 0:
                raise ValidationError("Hourly rate cannot be negative.")
            resource.hourly_rate = hourly_rate
        if is_active is not None:
            resource.is_active = is_active
        if cost_type is not None:
            resource.cost_type = cost_type
        if currency_code is not None:
            resource.currency_code = currency_code

        try:
            self._resource_repo.update(resource)
            self._session.commit()
            
        except Exception as e:
            self._session.rollback()
            raise e
        return resource

    def list_resources(self) -> List[Resource]:
        return self._resource_repo.list_all()

    def get_resource(self, resource_id: str) -> Resource:
        resource = self._resource_repo.get(resource_id)
        if not resource:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        return resource

    def delete_resource(self, resource_id: str) -> None:
        resource = self._resource_repo.get(resource_id)
        if not resource:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")

        try:
            # delete assignments and Project- Resource first
            assignments = self._assignment_repo.list_by_resource(resource_id)
            for a in assignments:
                self._assignment_repo.delete(a.id)
            if self._project_resource_repo is not None:
                self._project_resource_repo.delete_by_resource(resource_id)
                 
            self._resource_repo.delete(resource_id)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e


