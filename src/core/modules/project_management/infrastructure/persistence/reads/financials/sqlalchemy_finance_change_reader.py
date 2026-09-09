from __future__ import annotations

from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_change_facts import (
    FinancialChangeDetailFact,
    FinancialChangeImpactFact,
    FinancialChangeImpactQuery,
    FinancialChangeRequestQuery,
    FinancialChangeSummaryFact,
)
from src.core.modules.project_management.infrastructure.persistence.orm.budget import (
    ProjectBudgetORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_change import (
    FinancialChangeImpactORM,
    FinancialChangeRequestORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectCostCodeORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.forecast import (
    ProjectForecastORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM
from src.core.platform.infrastructure.persistence.orm.approval.approval import (
    ApprovalRequestORM,
)


_IMPACT_COUNT = (
    select(func.count(FinancialChangeImpactORM.id))
    .where(
        FinancialChangeImpactORM.tenant_id == FinancialChangeRequestORM.tenant_id,
        FinancialChangeImpactORM.organization_id
        == FinancialChangeRequestORM.organization_id,
        FinancialChangeImpactORM.project_id == FinancialChangeRequestORM.project_id,
        FinancialChangeImpactORM.change_request_id == FinancialChangeRequestORM.id,
    )
    .correlate(FinancialChangeRequestORM)
    .scalar_subquery()
)
_APPROVAL_STATUS = (
    select(ApprovalRequestORM.status)
    .where(
        ApprovalRequestORM.id == FinancialChangeRequestORM.approval_request_id,
        ApprovalRequestORM.tenant_id == FinancialChangeRequestORM.tenant_id,
        ApprovalRequestORM.organization_id == FinancialChangeRequestORM.organization_id,
        ApprovalRequestORM.project_id == FinancialChangeRequestORM.project_id,
    )
    .correlate(FinancialChangeRequestORM)
    .scalar_subquery()
)
_CHANGE_SORTS = {
    "title": FinancialChangeRequestORM.title,
    "statusLabel": FinancialChangeRequestORM.status,
    "subtitle": FinancialChangeRequestORM.revision,
    "supportingText": _IMPACT_COUNT,
    "metaText": FinancialChangeRequestORM.created_at,
}
_IMPACT_SORTS = {
    "title": FinancialChangeImpactORM.description,
    "statusLabel": FinancialChangeImpactORM.impact_type,
    "subtitle": FinancialChangeImpactORM.amount,
    "supportingText": func.coalesce(
        ProjectCostCodeORM.code, TaskORM.wbs_code, FinancialChangeImpactORM.target_line_id, ""
    ),
    "metaText": FinancialChangeImpactORM.created_at,
}
_CHANGE_STATUSES = {"draft", "pending_approval", "applied", "rejected"}
_IMPACT_TYPES = {"budget", "forecast", "schedule"}
_APPLIED_STATES = {"applied", "not_applied"}


class SqlAlchemyFinanceChangeReader:
    """Bounded Change Control projections; never mutates governed Finance state."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def list_changes(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinancialChangeRequestQuery,
    ) -> FinancePageFacts[FinancialChangeSummaryFact]:
        conditions = self._change_conditions(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
        )
        status = request.status.strip().lower()
        if status in _CHANGE_STATUSES:
            conditions.append(FinancialChangeRequestORM.status == status)
        approval_status = request.approval_status.strip().lower()
        if approval_status:
            conditions.append(func.lower(func.coalesce(_APPROVAL_STATUS, "")) == approval_status)
        applied_state = request.applied_state.strip().lower()
        if applied_state in _APPLIED_STATES:
            conditions.append(
                FinancialChangeRequestORM.status == "applied"
                if applied_state == "applied"
                else FinancialChangeRequestORM.status != "applied"
            )
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(
                    FinancialChangeRequestORM.title.ilike(pattern),
                    FinancialChangeRequestORM.reason.ilike(pattern),
                    FinancialChangeRequestORM.description.ilike(pattern),
                    FinancialChangeRequestORM.created_by.ilike(pattern),
                    FinancialChangeRequestORM.approval_request_id.ilike(pattern),
                )
            )

        total = int(
            self._session.scalar(
                select(func.count(FinancialChangeRequestORM.id)).where(*conditions)
            )
            or 0
        )
        page, page_size, offset = _normalized_window(
            request.normalized_page, request.normalized_page_size, total
        )
        sort_key = request.normalized_sort_key
        direction = "asc" if request.sort_direction == "asc" else "desc"
        expression = _CHANGE_SORTS[sort_key]
        ordered = expression.asc() if direction == "asc" else expression.desc()
        rows = self._session.execute(
            self._summary_projection()
            .where(*conditions)
            .order_by(ordered, FinancialChangeRequestORM.id.asc())
            .offset(offset)
            .limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(self._summary_fact(row) for row in rows),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=direction,
        )

    def get_change(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        change_id: str,
    ) -> FinancialChangeDetailFact | None:
        current_budget_id = _current_budget_value(
            ProjectBudgetORM.id, tenant_id, organization_id, project_id
        )
        current_budget_revision = _current_budget_value(
            ProjectBudgetORM.revision, tenant_id, organization_id, project_id
        )
        current_forecast_id = _current_forecast_value(
            ProjectForecastORM.id, tenant_id, organization_id, project_id
        )
        current_forecast_revision = _current_forecast_value(
            ProjectForecastORM.revision, tenant_id, organization_id, project_id
        )
        applied_budget_revision = _scoped_revision(
            ProjectBudgetORM,
            FinancialChangeRequestORM.applied_budget_id,
            tenant_id,
            organization_id,
            project_id,
        )
        applied_forecast_revision = _scoped_revision(
            ProjectForecastORM,
            FinancialChangeRequestORM.applied_forecast_id,
            tenant_id,
            organization_id,
            project_id,
        )
        row = self._session.execute(
            select(
                FinancialChangeRequestORM,
                _IMPACT_COUNT.label("impact_count"),
                current_budget_id.label("current_budget_id"),
                current_budget_revision.label("current_budget_revision"),
                current_forecast_id.label("current_forecast_id"),
                current_forecast_revision.label("current_forecast_revision"),
                applied_budget_revision.label("applied_budget_revision"),
                applied_forecast_revision.label("applied_forecast_revision"),
                ApprovalRequestORM.status.label("approval_status"),
                ApprovalRequestORM.requested_by_user_id,
                ApprovalRequestORM.requested_by_username,
                ApprovalRequestORM.requested_at,
                ApprovalRequestORM.decided_by_username,
                ApprovalRequestORM.decided_at,
                ApprovalRequestORM.decision_note,
            )
            .select_from(FinancialChangeRequestORM)
            .outerjoin(ApprovalRequestORM, _approval_join_scope())
            .where(
                *self._change_conditions(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                ),
                FinancialChangeRequestORM.id == change_id,
            )
        ).one_or_none()
        return self._detail_fact(row) if row is not None else None

    def list_impacts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        change_id: str,
        request: FinancialChangeImpactQuery,
    ) -> FinancePageFacts[FinancialChangeImpactFact]:
        conditions = self._impact_conditions(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            change_id=change_id,
        )
        impact_type = request.impact_type.strip().lower()
        if impact_type in _IMPACT_TYPES:
            conditions.append(FinancialChangeImpactORM.impact_type == impact_type)
        applied_state = request.applied_state.strip().lower()
        if applied_state in _APPLIED_STATES:
            conditions.append(
                FinancialChangeImpactORM.applied_reference_id.is_not(None)
                if applied_state == "applied"
                else FinancialChangeImpactORM.applied_reference_id.is_(None)
            )
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(
                    FinancialChangeImpactORM.description.ilike(pattern),
                    FinancialChangeImpactORM.target_line_id.ilike(pattern),
                    FinancialChangeImpactORM.applied_reference_id.ilike(pattern),
                    ProjectCostCodeORM.code.ilike(pattern),
                    ProjectCostCodeORM.name.ilike(pattern),
                    TaskORM.name.ilike(pattern),
                    TaskORM.wbs_code.ilike(pattern),
                )
            )
        base = self._impact_projection().where(*conditions)
        total = int(
            self._session.scalar(select(func.count()).select_from(base.subquery())) or 0
        )
        page, page_size, offset = _normalized_window(
            request.normalized_page, request.normalized_page_size, total
        )
        sort_key = request.normalized_sort_key
        direction = "asc" if request.sort_direction == "asc" else "desc"
        expression = _IMPACT_SORTS[sort_key]
        ordered = expression.asc() if direction == "asc" else expression.desc()
        rows = self._session.execute(
            base.order_by(ordered, FinancialChangeImpactORM.id.asc())
            .offset(offset)
            .limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(self._impact_fact(row) for row in rows),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=direction,
        )

    @staticmethod
    def _change_conditions(*, tenant_id: str, organization_id: str, project_id: str):
        return [
            FinancialChangeRequestORM.tenant_id == tenant_id,
            FinancialChangeRequestORM.organization_id == organization_id,
            FinancialChangeRequestORM.project_id == project_id,
        ]

    @staticmethod
    def _impact_conditions(
        *, tenant_id: str, organization_id: str, project_id: str, change_id: str
    ):
        return [
            FinancialChangeImpactORM.tenant_id == tenant_id,
            FinancialChangeImpactORM.organization_id == organization_id,
            FinancialChangeImpactORM.project_id == project_id,
            FinancialChangeImpactORM.change_request_id == change_id,
            FinancialChangeRequestORM.tenant_id == tenant_id,
            FinancialChangeRequestORM.organization_id == organization_id,
            FinancialChangeRequestORM.project_id == project_id,
            FinancialChangeRequestORM.id == change_id,
        ]

    @staticmethod
    def _summary_projection():
        return select(
            FinancialChangeRequestORM.id,
            FinancialChangeRequestORM.title,
            FinancialChangeRequestORM.status,
            FinancialChangeRequestORM.revision,
            FinancialChangeRequestORM.version,
            FinancialChangeRequestORM.effective_date,
            FinancialChangeRequestORM.currency_code,
            FinancialChangeRequestORM.reason,
            FinancialChangeRequestORM.created_by,
            FinancialChangeRequestORM.base_budget_id,
            FinancialChangeRequestORM.base_budget_revision,
            FinancialChangeRequestORM.base_forecast_id,
            FinancialChangeRequestORM.base_forecast_revision,
            _APPROVAL_STATUS.label("approval_status"),
            _IMPACT_COUNT.label("impact_count"),
            FinancialChangeRequestORM.created_at,
            FinancialChangeRequestORM.submitted_at,
            FinancialChangeRequestORM.applied_at,
        )

    @staticmethod
    def _summary_fact(row) -> FinancialChangeSummaryFact:
        return FinancialChangeSummaryFact(
            id=row.id,
            title=row.title,
            status=row.status,
            revision=row.revision,
            row_version=row.version,
            effective_date=row.effective_date,
            currency_code=row.currency_code,
            reason=row.reason,
            created_by=row.created_by,
            base_budget_id=row.base_budget_id,
            base_budget_revision=row.base_budget_revision,
            base_forecast_id=row.base_forecast_id,
            base_forecast_revision=row.base_forecast_revision,
            approval_status=row.approval_status or "",
            impact_count=int(row.impact_count or 0),
            created_at=row.created_at,
            submitted_at=row.submitted_at,
            applied_at=row.applied_at,
        )

    @staticmethod
    def _detail_fact(row) -> FinancialChangeDetailFact:
        change = row[0]
        return FinancialChangeDetailFact(
            id=change.id,
            title=change.title,
            status=change.status,
            revision=change.revision,
            row_version=change.version,
            reason=change.reason,
            description=change.description,
            effective_date=change.effective_date,
            currency_code=change.currency_code,
            created_by=change.created_by,
            created_at=change.created_at,
            updated_at=change.updated_at,
            base_budget_id=change.base_budget_id,
            base_budget_revision=change.base_budget_revision,
            current_budget_id=row.current_budget_id,
            current_budget_revision=row.current_budget_revision,
            base_budget_is_current=_is_current(
                change.base_budget_id,
                change.base_budget_revision,
                row.current_budget_id,
                row.current_budget_revision,
            ),
            base_forecast_id=change.base_forecast_id,
            base_forecast_revision=change.base_forecast_revision,
            current_forecast_id=row.current_forecast_id,
            current_forecast_revision=row.current_forecast_revision,
            base_forecast_is_current=_is_current(
                change.base_forecast_id,
                change.base_forecast_revision,
                row.current_forecast_id,
                row.current_forecast_revision,
            ),
            approval_request_id=change.approval_request_id,
            approval_status=row.approval_status or "",
            approval_requested_by=row.requested_by_username or "",
            approval_requested_by_user_id=row.requested_by_user_id,
            approval_requested_at=row.requested_at,
            approval_decided_by=row.decided_by_username or "",
            approval_decided_at=row.decided_at,
            approval_decision_note=row.decision_note or "",
            submitted_by=change.submitted_by,
            submitted_at=change.submitted_at,
            applied_by=change.applied_by,
            applied_at=change.applied_at,
            applied_budget_id=change.applied_budget_id,
            applied_budget_revision=row.applied_budget_revision,
            applied_forecast_id=change.applied_forecast_id,
            applied_forecast_revision=row.applied_forecast_revision,
            applied_schedule_count=change.applied_schedule_count,
            rejected_by=change.rejected_by,
            rejected_at=change.rejected_at,
            rejection_notes=change.rejection_notes,
            impact_count=int(row.impact_count or 0),
        )

    @staticmethod
    def _impact_projection():
        return (
            select(
                FinancialChangeImpactORM,
                ProjectCostCodeORM.code.label("cost_code"),
                ProjectCostCodeORM.name.label("cost_code_name"),
                TaskORM.name.label("task_name"),
                TaskORM.wbs_code,
            )
            .select_from(FinancialChangeImpactORM)
            .join(
                FinancialChangeRequestORM,
                and_(
                    FinancialChangeRequestORM.id
                    == FinancialChangeImpactORM.change_request_id,
                    FinancialChangeRequestORM.tenant_id
                    == FinancialChangeImpactORM.tenant_id,
                    FinancialChangeRequestORM.organization_id
                    == FinancialChangeImpactORM.organization_id,
                    FinancialChangeRequestORM.project_id
                    == FinancialChangeImpactORM.project_id,
                ),
            )
            .outerjoin(
                ProjectCostCodeORM,
                and_(
                    ProjectCostCodeORM.id == FinancialChangeImpactORM.cost_code_id,
                    ProjectCostCodeORM.tenant_id == FinancialChangeImpactORM.tenant_id,
                    ProjectCostCodeORM.organization_id
                    == FinancialChangeImpactORM.organization_id,
                ),
            )
            .outerjoin(
                TaskORM,
                and_(
                    TaskORM.id == FinancialChangeImpactORM.task_id,
                    TaskORM.project_id == FinancialChangeImpactORM.project_id,
                ),
            )
        )

    @staticmethod
    def _impact_fact(row) -> FinancialChangeImpactFact:
        impact = row[0]
        return FinancialChangeImpactFact(
            id=impact.id,
            change_request_id=impact.change_request_id,
            impact_type=impact.impact_type,
            description=impact.description,
            amount=Decimal(impact.amount),
            currency_code=impact.currency_code,
            cost_code_id=impact.cost_code_id,
            cost_code=row.cost_code or "",
            cost_code_name=row.cost_code_name or "",
            task_id=impact.task_id,
            task_name=row.task_name or "",
            wbs_code=row.wbs_code or "",
            target_line_id=impact.target_line_id,
            target_task_version=impact.target_task_version,
            schedule_start=impact.schedule_start,
            schedule_finish=impact.schedule_finish,
            applied_reference_type=impact.applied_reference_type,
            applied_reference_id=impact.applied_reference_id,
            row_version=impact.version,
            created_at=impact.created_at,
            updated_at=impact.updated_at,
        )


def _approval_join_scope():
    return and_(
        ApprovalRequestORM.id == FinancialChangeRequestORM.approval_request_id,
        ApprovalRequestORM.tenant_id == FinancialChangeRequestORM.tenant_id,
        ApprovalRequestORM.organization_id == FinancialChangeRequestORM.organization_id,
        ApprovalRequestORM.project_id == FinancialChangeRequestORM.project_id,
    )


def _current_budget_value(column, tenant_id: str, organization_id: str, project_id: str):
    return (
        select(column)
        .where(
            ProjectBudgetORM.tenant_id == tenant_id,
            ProjectBudgetORM.organization_id == organization_id,
            ProjectBudgetORM.project_id == project_id,
            ProjectBudgetORM.status == "approved",
        )
        .limit(1)
        .scalar_subquery()
    )


def _current_forecast_value(column, tenant_id: str, organization_id: str, project_id: str):
    return (
        select(column)
        .where(
            ProjectForecastORM.tenant_id == tenant_id,
            ProjectForecastORM.organization_id == organization_id,
            ProjectForecastORM.project_id == project_id,
            ProjectForecastORM.status == "approved",
        )
        .limit(1)
        .scalar_subquery()
    )


def _scoped_revision(model, requested_id, tenant_id: str, organization_id: str, project_id: str):
    return (
        select(model.revision)
        .where(
            model.id == requested_id,
            model.tenant_id == tenant_id,
            model.organization_id == organization_id,
            model.project_id == project_id,
        )
        .limit(1)
        .scalar_subquery()
    )


def _is_current(base_id, base_revision, current_id, current_revision) -> bool | None:
    if base_id is None:
        return None
    return base_id == current_id and base_revision == current_revision


def _normalized_window(page: int, page_size: int, total: int) -> tuple[int, int, int]:
    last_page = max(1, (max(0, total) + page_size - 1) // page_size)
    normalized_page = min(page, last_page)
    return normalized_page, page_size, (normalized_page - 1) * page_size


__all__ = ["SqlAlchemyFinanceChangeReader"]
