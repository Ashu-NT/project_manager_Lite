from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.interfaces import ProjectRepository, ProjectResourceRepository
from core.models import Project, ProjectResource
from infra.db.models import ProjectORM, ProjectResourceORM
from infra.db.optimistic import update_with_version_check
from infra.db.project.mapper import (
    project_from_orm,
    project_resource_from_orm,
    project_resource_to_orm,
    project_to_orm,
)


class SqlAlchemyProjectRepository(ProjectRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, project: Project) -> None:
        self.session.add(project_to_orm(project))

    def update(self, project: Project) -> None:
        project.version = update_with_version_check(
            self.session,
            ProjectORM,
            project.id,
            getattr(project, "version", 1),
            {
                "name": project.name,
                "description": project.description,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "status": project.status,
                "client_name": project.client_name,
                "client_contact": project.client_contact,
                "planned_budget": project.planned_budget,
                "currency": project.currency,
            },
            not_found_message="Project not found.",
            stale_message="Project was updated by another user.",
        )

    def delete(self, project_id: str) -> None:
        self.session.query(ProjectORM).filter_by(id=project_id).delete()

    def get(self, project_id: str) -> Optional[Project]:
        obj = self.session.get(ProjectORM, project_id)
        return project_from_orm(obj) if obj else None

    def list_all(self) -> List[Project]:
        stmt = select(ProjectORM)
        rows = self.session.execute(stmt).scalars().all()
        return [project_from_orm(row) for row in rows]


class SqlAlchemyProjectResourceRepository(ProjectResourceRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, pr: ProjectResource) -> None:
        self.session.add(project_resource_to_orm(pr))

    def get(self, pr_id: str) -> Optional[ProjectResource]:
        obj = self.session.get(ProjectResourceORM, pr_id)
        return project_resource_from_orm(obj) if obj else None

    def list_by_project(self, project_id: str) -> List[ProjectResource]:
        stmt = select(ProjectResourceORM).where(ProjectResourceORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [project_resource_from_orm(row) for row in rows]

    def get_for_project(self, project_id: str, resource_id: str) -> Optional[ProjectResource]:
        stmt = select(ProjectResourceORM).where(
            ProjectResourceORM.project_id == project_id,
            ProjectResourceORM.resource_id == resource_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return project_resource_from_orm(obj) if obj else None

    def delete(self, pr_id: str) -> None:
        obj = self.session.get(ProjectResourceORM, pr_id)
        if obj:
            self.session.delete(obj)

    def delete_by_resource(self, res_id: str) -> None:
        self.session.query(ProjectResourceORM).filter_by(resource_id=res_id).delete()

    def update(self, pr: ProjectResource) -> None:
        self.session.merge(project_resource_to_orm(pr))


__all__ = [
    "SqlAlchemyProjectRepository",
    "SqlAlchemyProjectResourceRepository",
]
