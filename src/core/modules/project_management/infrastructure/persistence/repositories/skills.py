"""SQLAlchemy repositories for resource skills and certifications."""

from __future__ import annotations


from sqlalchemy import delete
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
from src.core.modules.project_management.infrastructure.persistence.repositories._tenant_scope import (
    ProjectManagementParentScopedRepositorySupport,
)
from src.core.modules.project_management.infrastructure.persistence.orm.skills import (
    ResourceCertificationORM,
    ResourceSkillORM,
    TaskSkillRequirementORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM
from src.core.platform.tenancy.tenant_context import TenantContextService


class SqlAlchemyResourceSkillRepository(
    ProjectManagementParentScopedRepositorySupport,
    ResourceSkillRepository,
):
    _repository_label = "Resource skill repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._session = session
        self._tenant_context_service: TenantContextService | None = None

    def _resource_skill_scoped_stmt(self, *, operation_label: str):
        return self._scoped_stmt_for_anchor(
            ResourceSkillORM,
            ResourceORM,
            joins=((ResourceORM, ResourceSkillORM.resource_id == ResourceORM.id),),
            operation_label=operation_label,
        )

    def _ensure_resource_in_scope(self, resource_id: str) -> None:
        self._require_anchor_in_scope(
            ResourceORM,
            resource_id,
            operation_label="manage resource skills",
            not_found_message="Resource not found.",
        )

    def add(self, skill: ResourceSkill) -> ResourceSkill:
        self._ensure_resource_in_scope(skill.resource_id)
        orm_obj = skill_to_orm(skill)
        self.session.add(orm_obj)
        self.session.flush()
        return skill

    def get(self, skill_id: str) -> ResourceSkill | None:
        stmt = self._resource_skill_scoped_stmt(
            operation_label="access resource skills"
        ).where(ResourceSkillORM.id == skill_id)
        obj = self.session.execute(stmt).scalar_one_or_none()
        return skill_from_orm(obj) if obj else None

    def list_by_resource(self, resource_id: str) -> list[ResourceSkill]:
        stmt = (
            self._resource_skill_scoped_stmt(operation_label="access resource skills")
            .where(ResourceSkillORM.resource_id == resource_id)
            .order_by(ResourceSkillORM.skill_name)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [skill_from_orm(row) for row in rows]

    def delete(self, skill_id: str) -> None:
        scoped_ids = (
            self._resource_skill_scoped_stmt(operation_label="manage resource skills")
            .where(ResourceSkillORM.id == skill_id)
            .with_only_columns(ResourceSkillORM.id)
            .scalar_subquery()
        )
        self.session.execute(delete(ResourceSkillORM).where(ResourceSkillORM.id == scoped_ids))


class SqlAlchemyResourceCertificationRepository(
    ProjectManagementParentScopedRepositorySupport,
    ResourceCertificationRepository,
):
    _repository_label = "Resource certification repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._session = session
        self._tenant_context_service: TenantContextService | None = None

    def _resource_cert_scoped_stmt(self, *, operation_label: str):
        return self._scoped_stmt_for_anchor(
            ResourceCertificationORM,
            ResourceORM,
            joins=((ResourceORM, ResourceCertificationORM.resource_id == ResourceORM.id),),
            operation_label=operation_label,
        )

    def _ensure_resource_in_scope(self, resource_id: str) -> None:
        self._require_anchor_in_scope(
            ResourceORM,
            resource_id,
            operation_label="manage resource certifications",
            not_found_message="Resource not found.",
        )

    def add(self, cert: ResourceCertification) -> ResourceCertification:
        self._ensure_resource_in_scope(cert.resource_id)
        orm_obj = cert_to_orm(cert)
        self.session.add(orm_obj)
        self.session.flush()
        return cert

    def get(self, cert_id: str) -> ResourceCertification | None:
        stmt = self._resource_cert_scoped_stmt(
            operation_label="access resource certifications"
        ).where(ResourceCertificationORM.id == cert_id)
        obj = self.session.execute(stmt).scalar_one_or_none()
        return cert_from_orm(obj) if obj else None

    def list_by_resource(self, resource_id: str) -> list[ResourceCertification]:
        stmt = (
            self._resource_cert_scoped_stmt(
                operation_label="access resource certifications"
            )
            .where(ResourceCertificationORM.resource_id == resource_id)
            .order_by(ResourceCertificationORM.certification_name)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [cert_from_orm(row) for row in rows]

    def delete(self, cert_id: str) -> None:
        scoped_ids = (
            self._resource_cert_scoped_stmt(
                operation_label="manage resource certifications"
            )
            .where(ResourceCertificationORM.id == cert_id)
            .with_only_columns(ResourceCertificationORM.id)
            .scalar_subquery()
        )
        self.session.execute(
            delete(ResourceCertificationORM).where(ResourceCertificationORM.id == scoped_ids)
        )


class SqlAlchemyTaskSkillRequirementRepository(
    ProjectManagementParentScopedRepositorySupport,
    TaskSkillRequirementRepository,
):
    _repository_label = "Task skill requirement repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._session = session
        self._tenant_context_service: TenantContextService | None = None

    def _task_requirement_scoped_stmt(self, *, operation_label: str):
        return self._scoped_stmt_for_anchor(
            TaskSkillRequirementORM,
            ProjectORM,
            joins=(
                (TaskORM, TaskSkillRequirementORM.task_id == TaskORM.id),
                (ProjectORM, TaskORM.project_id == ProjectORM.id),
            ),
            operation_label=operation_label,
        )

    def _ensure_task_in_scope(self, task_id: str) -> None:
        self._require_anchor_in_scope(
            TaskORM,
            task_id,
            operation_label="manage task skill requirements",
            not_found_message="Task not found.",
            joins=((ProjectORM, TaskORM.project_id == ProjectORM.id),),
            scope_model=ProjectORM,
        )

    def add(self, req: TaskSkillRequirement) -> TaskSkillRequirement:
        self._ensure_task_in_scope(req.task_id)
        orm_obj = task_req_to_orm(req)
        self.session.add(orm_obj)
        self.session.flush()
        return req

    def get(self, req_id: str) -> TaskSkillRequirement | None:
        stmt = self._task_requirement_scoped_stmt(
            operation_label="access task skill requirements"
        ).where(TaskSkillRequirementORM.id == req_id)
        obj = self.session.execute(stmt).scalar_one_or_none()
        return task_req_from_orm(obj) if obj else None

    def list_by_task(self, task_id: str) -> list[TaskSkillRequirement]:
        stmt = (
            self._task_requirement_scoped_stmt(
                operation_label="access task skill requirements"
            )
            .where(TaskSkillRequirementORM.task_id == task_id)
            .order_by(TaskSkillRequirementORM.skill_code, TaskSkillRequirementORM.certification_code)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [task_req_from_orm(row) for row in rows]

    def delete(self, req_id: str) -> None:
        scoped_ids = (
            self._task_requirement_scoped_stmt(
                operation_label="manage task skill requirements"
            )
            .where(TaskSkillRequirementORM.id == req_id)
            .with_only_columns(TaskSkillRequirementORM.id)
            .scalar_subquery()
        )
        self.session.execute(
            delete(TaskSkillRequirementORM).where(TaskSkillRequirementORM.id == scoped_ids)
        )


__all__ = [
    "SqlAlchemyResourceCertificationRepository",
    "SqlAlchemyResourceSkillRepository",
    "SqlAlchemyTaskSkillRequirementRepository",
]
