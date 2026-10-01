from sqlalchemy import Date, cast, func, null, select

from src.core.global_overview.contract.action_center import ActionCenterContribution, ActionCenterItemDto, ActionCenterSummaryDto
from src.core.platform.infrastructure.persistence.common.approval_eligibility import approval_reviewer_eligibility
from src.core.platform.infrastructure.persistence.orm.approval.approval import ApprovalRequestORM
from src.core.global_overview.infrastructure.persistence.reads.action_center import action_window


class SqlAlchemyPlatformActionCenterReader:
    def __init__(self, *, session, target_scope_predicate):
        self._session = session
        self._target_scope_predicate = target_scope_predicate

    def collect(self, context, preview_limit, *, after=None):
        request = ApprovalRequestORM
        base = select(request.id, request.entity_type, request.entity_id, request.requested_at).where(
            request.tenant_id == context.tenant_id,
            request.organization_id == context.organization_id,
            self._target_scope_predicate,
            approval_reviewer_eligibility(context.user_id),
        )
        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        rows = self._session.execute(action_window(
            base, due=cast(null(), Date), recency=request.requested_at,
            module="Platform", kind="approval", identity=request.id, after=after, limit=preview_limit,
        )).all() if preview_limit else ()
        items = tuple(ActionCenterItemDto(
            id=row.id, kind="approval", title="Review " + row.entity_type.replace("_", " "),
            module="Platform", subject_type=row.entity_type, subject_id=row.entity_id,
            subject_display=row.entity_type.replace("_", " ").title(), action_state="awaiting_decision",
            route_id="control_approvals", sort_at=row.requested_at,
        ) for row in rows)
        return ActionCenterContribution(items, ActionCenterSummaryDto(total, total, 0, 0))
