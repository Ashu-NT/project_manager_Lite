"""SQLAlchemy repositories for resource skills and certifications."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.skills import (
    ResourceCertificationRepository,
    ResourceSkillRepository,
)
from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.skills import (
    cert_from_orm,
    cert_to_orm,
    skill_from_orm,
    skill_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.skills import (
    ResourceCertificationORM,
    ResourceSkillORM,
)


class SqlAlchemyResourceSkillRepository(ResourceSkillRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, skill: ResourceSkill) -> ResourceSkill:
        orm_obj = skill_to_orm(skill)
        self._session.add(orm_obj)
        self._session.flush()
        return skill

    def get(self, skill_id: str) -> Optional[ResourceSkill]:
        obj = self._session.get(ResourceSkillORM, skill_id)
        return skill_from_orm(obj) if obj else None

    def list_by_resource(self, resource_id: str) -> List[ResourceSkill]:
        stmt = (
            select(ResourceSkillORM)
            .where(ResourceSkillORM.resource_id == resource_id)
            .order_by(ResourceSkillORM.skill_name)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [skill_from_orm(row) for row in rows]

    def delete(self, skill_id: str) -> None:
        self._session.query(ResourceSkillORM).filter_by(id=skill_id).delete()


class SqlAlchemyResourceCertificationRepository(ResourceCertificationRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, cert: ResourceCertification) -> ResourceCertification:
        orm_obj = cert_to_orm(cert)
        self._session.add(orm_obj)
        self._session.flush()
        return cert

    def get(self, cert_id: str) -> Optional[ResourceCertification]:
        obj = self._session.get(ResourceCertificationORM, cert_id)
        return cert_from_orm(obj) if obj else None

    def list_by_resource(self, resource_id: str) -> List[ResourceCertification]:
        stmt = (
            select(ResourceCertificationORM)
            .where(ResourceCertificationORM.resource_id == resource_id)
            .order_by(ResourceCertificationORM.certification_name)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [cert_from_orm(row) for row in rows]

    def delete(self, cert_id: str) -> None:
        self._session.query(ResourceCertificationORM).filter_by(id=cert_id).delete()


__all__ = [
    "SqlAlchemyResourceCertificationRepository",
    "SqlAlchemyResourceSkillRepository",
]
