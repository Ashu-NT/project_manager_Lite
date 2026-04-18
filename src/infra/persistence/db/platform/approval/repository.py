from __future__ import annotations

from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.core.platform.approval.contracts import ApprovalRepository
from src.core.platform.approval.domain import ApprovalRequest, ApprovalStatus
from src.infra.persistence.db.platform.approval.mapper import approval_from_orm, approval_to_orm
from src.infra.persistence.orm.platform.models import ApprovalRequestORM


class SqlAlchemyApprovalRepository(ApprovalRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, request: ApprovalRequest) -> None:
        self.session.add(approval_to_orm(request))

    def update(self, request: ApprovalRequest) -> None:
        obj = self.session.get(ApprovalRequestORM, request.id)
        if obj is None:
            self.session.add(approval_to_orm(request))
            return
        obj.request_type = request.request_type
        obj.entity_type = request.entity_type
        obj.entity_id = request.entity_id
        obj.project_id = request.project_id
        obj.payload_json = approval_to_orm(request).payload_json
        obj.status = request.status.value
        obj.requested_by_user_id = request.requested_by_user_id
        obj.requested_by_username = request.requested_by_username
        obj.requested_at = request.requested_at
        obj.decided_by_user_id = request.decided_by_user_id
        obj.decided_by_username = request.decided_by_username
        obj.decided_at = request.decided_at
        obj.decision_note = request.decision_note

    def get(self, request_id: str) -> Optional[ApprovalRequest]:
        obj = self.session.get(ApprovalRequestORM, request_id)
        return approval_from_orm(obj) if obj else None

    def list_by_status(
        self,
        status: ApprovalStatus | None = None,
        *,
        limit: int = 200,
        project_id: str | None = None,
        entity_type: str | list[str] | None = None,
        entity_id: str | None = None,
    ) -> List[ApprovalRequest]:
        stmt = select(ApprovalRequestORM)
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

