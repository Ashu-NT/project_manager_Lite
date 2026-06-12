from __future__ import annotations

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.platform.approval.contracts import ApprovalRepository
from src.core.platform.approval.domain import ApprovalRequest, ApprovalStatus
from src.core.platform.infrastructure.persistence.mappers.approval import approval_from_orm, approval_to_orm
from src.core.platform.infrastructure.persistence.orm.approval import ApprovalRequestORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)


class SqlAlchemyApprovalRepository(TenantScopedRepositorySupport, ApprovalRepository):
    _repository_label = "ApprovalRepository"
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, request: ApprovalRequest) -> None:
        ctx = self._context(operation_label="access approvals")
        orm = approval_to_orm(request)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self.session.add(orm)

    def update(self, request: ApprovalRequest) -> None:
        ctx = self._context(operation_label="access approvals")
        obj = self.session.execute(
            select(ApprovalRequestORM).where(
                ApprovalRequestORM.id == request.id,
                ApprovalRequestORM.tenant_id == ctx.tenant_id,
                ApprovalRequestORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if obj is None:
            orm = approval_to_orm(request)
            orm.tenant_id = ctx.tenant_id
            orm.organization_id = ctx.organization_id
            self.session.add(orm)
            return
        obj.request_type = request.request_type
        obj.entity_type = request.entity_type
        obj.entity_id = request.entity_id
        obj.project_id = request.project_id
        obj.organization_id = ctx.organization_id
        obj.payload_json = approval_to_orm(request).payload_json
        obj.status = request.status.value
        obj.requested_by_user_id = request.requested_by_user_id
        obj.requested_by_username = request.requested_by_username
        obj.requested_at = request.requested_at
        obj.decided_by_user_id = request.decided_by_user_id
        obj.decided_by_username = request.decided_by_username
        obj.decided_at = request.decided_at
        obj.decision_note = request.decision_note

    def get(self, request_id: str) -> ApprovalRequest | None:
        ctx = self._context(operation_label="access approvals")
        stmt = (
            select(ApprovalRequestORM)
            .outerjoin(
                ProjectORM,
                and_(
                    ProjectORM.id == ApprovalRequestORM.project_id,
                    ProjectORM.tenant_id == ctx.tenant_id,
                ),
            )
            .where(
                ApprovalRequestORM.id == request_id,
                ApprovalRequestORM.tenant_id == ctx.tenant_id,
                or_(
                    ApprovalRequestORM.organization_id == ctx.organization_id,
                    ProjectORM.organization_id == ctx.organization_id,
                ),
            )
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        return approval_from_orm(obj) if obj else None

    def list_by_status(
        self,
        status: ApprovalStatus | None = None,
        *,
        limit: int = 200,
        project_id: str | None = None,
        entity_type: str | list[str] | None = None,
        entity_id: str | None = None,
    ) -> list[ApprovalRequest]:
        ctx = self._context(operation_label="access approvals")
        stmt = (
            select(ApprovalRequestORM)
            .outerjoin(
                ProjectORM,
                and_(
                    ProjectORM.id == ApprovalRequestORM.project_id,
                    ProjectORM.tenant_id == ctx.tenant_id,
                ),
            )
            .where(
                ApprovalRequestORM.tenant_id == ctx.tenant_id,
                or_(
                    ApprovalRequestORM.organization_id == ctx.organization_id,
                    ProjectORM.organization_id == ctx.organization_id,
                ),
            )
        )
        if status is not None:
            stmt = stmt.where(ApprovalRequestORM.status == status.value)
        if project_id is not None:
            stmt = stmt.where(ApprovalRequestORM.project_id == project_id)
        if entity_type is not None:
            if isinstance(entity_type, str):
                stmt = stmt.where(ApprovalRequestORM.entity_type == entity_type)
            else:
                stmt = stmt.where(ApprovalRequestORM.entity_type.in_(entity_type))
        if entity_id is not None:
            stmt = stmt.where(ApprovalRequestORM.entity_id == entity_id)
        stmt = stmt.order_by(desc(ApprovalRequestORM.requested_at)).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [approval_from_orm(row) for row in rows]

    def project_belongs_to_organization(self, project_id: str, organization_id: str) -> bool:
        ctx = self._context(operation_label="access approvals")
        if organization_id != ctx.organization_id:
            return False
        stmt = select(ProjectORM.id).where(
            ProjectORM.id == project_id,
            ProjectORM.tenant_id == ctx.tenant_id,
            ProjectORM.organization_id == ctx.organization_id,
        )
        return self.session.execute(stmt).first() is not None

    def list_by_status_for_organization(
        self,
        organization_id: str,
        status: ApprovalStatus | None = None,
        *,
        limit: int = 200,
        project_id: str | None = None,
        entity_type: str | list[str] | None = None,
        entity_id: str | None = None,
    ) -> list[ApprovalRequest]:
        ctx = self._context(operation_label="access approvals")
        if organization_id != ctx.organization_id:
            return []
        stmt = (
            select(ApprovalRequestORM)
            .outerjoin(
                ProjectORM,
                and_(
                    ProjectORM.id == ApprovalRequestORM.project_id,
                    ProjectORM.tenant_id == ctx.tenant_id,
                ),
            )
            .where(
                ApprovalRequestORM.tenant_id == ctx.tenant_id,
                or_(
                    ApprovalRequestORM.organization_id == ctx.organization_id,
                    ProjectORM.organization_id == ctx.organization_id,
                )
            )
        )
        if status is not None:
            stmt = stmt.where(ApprovalRequestORM.status == status.value)
        if project_id is not None:
            stmt = stmt.where(ApprovalRequestORM.project_id == project_id)
        if entity_type is not None:
            if isinstance(entity_type, str):
                stmt = stmt.where(ApprovalRequestORM.entity_type == entity_type)
            else:
                stmt = stmt.where(ApprovalRequestORM.entity_type.in_(entity_type))
        if entity_id is not None:
            stmt = stmt.where(ApprovalRequestORM.entity_id == entity_id)
        stmt = stmt.order_by(desc(ApprovalRequestORM.requested_at)).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [approval_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyApprovalRepository"]
