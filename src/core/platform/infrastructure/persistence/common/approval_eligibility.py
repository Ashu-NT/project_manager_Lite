"""Shared reviewer eligibility for notification targeting and actionable reads."""

from sqlalchemy import and_, or_

from src.core.platform.infrastructure.persistence.common.scoped_permission import (
    scoped_permission,
)
from src.core.platform.infrastructure.persistence.orm.approval.approval import (
    ApprovalRequestORM,
)


def approval_reviewer_eligibility(user_id):
    request = ApprovalRequestORM
    return and_(
        request.status == "PENDING",
        or_(request.requested_by_user_id.is_(None), request.requested_by_user_id != user_id),
        scoped_permission(user_id=user_id, tenant_id=request.tenant_id,
                          organization_id=request.organization_id, project_id=request.project_id,
                          permissions=("approval.decide",)),
    )
