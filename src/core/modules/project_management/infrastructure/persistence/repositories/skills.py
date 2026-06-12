"""SQLAlchemy repositories for resource skills and certifications."""

from __future__ import annotations


from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.skills import (
    ResourceCertificationRepository,
    ResourceSkillRepository,
    TaskSkillRequirementRepository,
)
from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
    TaskSkillRequirement,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.skills import (
    cert_from_orm,
    cert_to_orm,
    skill_from_orm,
    skill_to_orm,
    task_req_from_orm,
    task_req_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.skills import (
    ResourceCertificationORM,
    ResourceSkillORM,
    TaskSkillRequirementORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM
from src.core.platform.tenancy.tenant_context import TenantContextService


class SqlAlchemyResourceSkillRepository(ResourceSkillRepository):
    def __init__(self, session: Session) -> None:
        self._session = session
        self._tenant_context_service: TenantContextService | None = None

    def _scoped_resource_ids(self):
        if self._tenant_context_service is None:
            return None
        ctx = self._tenant_context_service.require_organization_context(
            operation_label="access resource skills"
        )
        return select(ResourceORM.id).where(
            ResourceORM.tenant_id == ctx.tenant_id,
            ResourceORM.organization_id == ctx.organization_id,
        )

    def add(self, skill: ResourceSkill) -> ResourceSkill:
        orm_obj = skill_to_orm(skill)
        self._session.add(orm_obj)
        self._session.flush()
        return skill

    def get(self, skill_id: str) -> ResourceSkill | None:
        scoped_ids = self._scoped_resource_ids()
        if scoped_ids is not None:
            stmt = select(ResourceSkillORM).where(
                ResourceSkillORM.id == skill_id,
                ResourceSkillORM.resource_id.in_(scoped_ids),
            )
            obj = self._session.execute(stmt).scalar_one_or_none()
        else:
            obj = self._session.get(ResourceSkillORM, skill_id)
        return skill_from_orm(obj) if obj else None

    def list_by_resource(self, resource_id: str) -> list[ResourceSkill]:
        stmt = (
            select(ResourceSkillORM)
            .where(ResourceSkillORM.resource_id == resource_id)
            .order_by(ResourceSkillORM.skill_name)
        )
        scoped_ids = self._scoped_resource_ids()
        if scoped_ids is not None:
            stmt = stmt.where(ResourceSkillORM.resource_id.in_(scoped_ids))
        rows = self._session.execute(stmt).scalars().all()
        return [skill_from_orm(row) for row in rows]

    def delete(self, skill_id: str) -> None:
        scoped_ids = self._scoped_resource_ids()
        if scoped_ids is not None:
            self._session.execute(
                delete(ResourceSkillORM).where(
                    ResourceSkillORM.id == skill_id,
                    ResourceSkillORM.resource_id.in_(scoped_ids),
                )
            )
        else:
            self._session.query(ResourceSkillORM).filter_by(id=skill_id).delete()


class SqlAlchemyResourceCertificationRepository(ResourceCertificationRepository):
    def __init__(self, session: Session) -> None:
        self._session = session
        self._tenant_context_service: TenantContextService | None = None

    def _scoped_resource_ids(self):
        if self._tenant_context_service is None:
            return None
        ctx = self._tenant_context_service.require_organization_context(
            operation_label="access resource certifications"
        )
        return select(ResourceORM.id).where(
            ResourceORM.tenant_id == ctx.tenant_id,
            ResourceORM.organization_id == ctx.organization_id,
        )

    def add(self, cert: ResourceCertification) -> ResourceCertification:
        orm_obj = cert_to_orm(cert)
        self._session.add(orm_obj)
        self._session.flush()
        return cert

    def get(self, cert_id: str) -> ResourceCertification | None:
        scoped_ids = self._scoped_resource_ids()
        if scoped_ids is not None:
            stmt = select(ResourceCertificationORM).where(
                ResourceCertificationORM.id == cert_id,
                ResourceCertificationORM.resource_id.in_(scoped_ids),
            )
            obj = self._session.execute(stmt).scalar_one_or_none()
        else:
            obj = self._session.get(ResourceCertificationORM, cert_id)
        return cert_from_orm(obj) if obj else None

    def list_by_resource(self, resource_id: str) -> list[ResourceCertification]:
        stmt = (
            select(ResourceCertificationORM)
            .where(ResourceCertificationORM.resource_id == resource_id)
            .order_by(ResourceCertificationORM.certification_name)
        )
        scoped_ids = self._scoped_resource_ids()
        if scoped_ids is not None:
            stmt = stmt.where(ResourceCertificationORM.resource_id.in_(scoped_ids))
        rows = self._session.execute(stmt).scalars().all()
        return [cert_from_orm(row) for row in rows]

    def delete(self, cert_id: str) -> None:
        scoped_ids = self._scoped_resource_ids()
        if scoped_ids is not None:
            self._session.execute(
                delete(ResourceCertificationORM).where(
                    ResourceCertificationORM.id == cert_id,
                    ResourceCertificationORM.resource_id.in_(scoped_ids),
                )
            )
        else:
            self._session.query(ResourceCertificationORM).filter_by(id=cert_id).delete()


class SqlAlchemyTaskSkillRequirementRepository(TaskSkillRequirementRepository):
    def __init__(self, session: Session) -> None:
        self._session = session
        self._tenant_context_service: TenantContextService | None = None

    def _scoped_task_ids(self):
        if self._tenant_context_service is None:
            return None
        ctx = self._tenant_context_service.require_organization_context(
            operation_label="access task skill requirements"
        )
        return (
            select(TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )

    def add(self, req: TaskSkillRequirement) -> TaskSkillRequirement:
        orm_obj = task_req_to_orm(req)
        self._session.add(orm_obj)
        self._session.flush()
        return req

    def get(self, req_id: str) -> TaskSkillRequirement | None:
        scoped_ids = self._scoped_task_ids()
        if scoped_ids is not None:
            stmt = select(TaskSkillRequirementORM).where(
                TaskSkillRequirementORM.id == req_id,
                TaskSkillRequirementORM.task_id.in_(scoped_ids),
            )
            obj = self._session.execute(stmt).scalar_one_or_none()
        else:
            obj = self._session.get(TaskSkillRequirementORM, req_id)
        return task_req_from_orm(obj) if obj else None

    def list_by_task(self, task_id: str) -> list[TaskSkillRequirement]:
        stmt = (
            select(TaskSkillRequirementORM)
            .where(TaskSkillRequirementORM.task_id == task_id)
            .order_by(TaskSkillRequirementORM.skill_code, TaskSkillRequirementORM.certification_code)
        )
        scoped_ids = self._scoped_task_ids()
        if scoped_ids is not None:
            stmt = stmt.where(TaskSkillRequirementORM.task_id.in_(scoped_ids))
        rows = self._session.execute(stmt).scalars().all()
        return [task_req_from_orm(row) for row in rows]

    def delete(self, req_id: str) -> None:
        scoped_ids = self._scoped_task_ids()
        if scoped_ids is not None:
            self._session.execute(
                delete(TaskSkillRequirementORM).where(
                    TaskSkillRequirementORM.id == req_id,
                    TaskSkillRequirementORM.task_id.in_(scoped_ids),
                )
            )
        else:
            self._session.query(TaskSkillRequirementORM).filter_by(id=req_id).delete()


__all__ = [
    "SqlAlchemyResourceCertificationRepository",
    "SqlAlchemyResourceSkillRepository",
    "SqlAlchemyTaskSkillRequirementRepository",
]
