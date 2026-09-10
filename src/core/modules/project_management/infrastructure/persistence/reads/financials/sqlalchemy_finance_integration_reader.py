from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_integration_facts import (
    ApprovedTimePostingFailureFact,
    ApprovedTimePostingFailurePage,
    ApprovedTimePostingFailureQuery,
)
from src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox import (
    ProjectFinanceInboxORM,
)
from src.core.platform.integration import APPROVED_TIME_ENTRY_EVENT_TYPE


_SORTS = {
    "source": ProjectFinanceInboxORM.aggregate_id,
    "status": ProjectFinanceInboxORM.status,
    "failure": ProjectFinanceInboxORM.last_error_code,
    "attempts": ProjectFinanceInboxORM.attempt_count,
    "updated": ProjectFinanceInboxORM.updated_at,
}
_FAILURE_STATUSES = ("processing", "retry", "quarantined", "dead_letter")


def _failure_category(code: str) -> str:
    if code.startswith("RATE_CARD_"):
        return "Rate configuration"
    if code.startswith("FINANCIAL_PERIOD_"):
        return "Financial period"
    if "COST_CODE" in code or code == "FINANCIAL_PROFILE_REQUIRED":
        return "Financial setup"
    if "REVISION" in code or "HASH" in code or code == "STALE_AGGREGATE_VERSION":
        return "Source conflict"
    if "SCOPE" in code or "PRINCIPAL" in code or "ACCOUNT" in code:
        return "Security configuration"
    return "Technical delivery"


def _corrective_action(code: str, status: str) -> str:
    if code == "RATE_CARD_NO_APPLICABLE_RATE":
        return "Configure an applicable project cost rate; automatic retry will reuse this event."
    if code in {"RATE_CARD_AMBIGUOUS_SELECTION", "RATE_CARD_MODIFIER_NOT_CONFIGURED"}:
        return "Correct the project Rate Card configuration; automatic retry will reuse this event."
    if code.startswith("FINANCIAL_PERIOD_"):
        return "Open or configure the financial period for the work date."
    if "COST_CODE" in code or code == "FINANCIAL_PROFILE_REQUIRED":
        return "Correct the project financial profile and default Cost Code."
    if status in {"quarantined", "dead_letter"}:
        return "Review the immutable source conflict or security configuration with an administrator."
    return "Review the integration error; transient failures retry automatically."


class SqlAlchemyFinanceIntegrationReader:
    """Bounded, tenant-scoped diagnostics over the canonical Finance inbox."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def list_approved_time_failures(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: ApprovedTimePostingFailureQuery,
    ) -> ApprovedTimePostingFailurePage:
        conditions = (
            ProjectFinanceInboxORM.tenant_id == tenant_id,
            ProjectFinanceInboxORM.organization_id == organization_id,
            ProjectFinanceInboxORM.source_project_id == project_id,
            ProjectFinanceInboxORM.event_type == APPROVED_TIME_ENTRY_EVENT_TYPE,
            ProjectFinanceInboxORM.status.in_(_FAILURE_STATUSES),
        )
        if request.normalized_status:
            conditions = (*conditions, ProjectFinanceInboxORM.status == request.normalized_status)
        total = int(
            self._session.scalar(
                select(func.count(ProjectFinanceInboxORM.id)).where(*conditions)
            )
            or 0
        )
        page_size = request.normalized_page_size
        last_page = max(1, (total + page_size - 1) // page_size)
        page = min(request.normalized_page, last_page)
        sort_key = request.normalized_sort_key
        direction = "asc" if request.sort_direction == "asc" else "desc"
        expression = _SORTS[sort_key]
        ordered = expression.asc() if direction == "asc" else expression.desc()
        rows = self._session.execute(
            select(ProjectFinanceInboxORM)
            .where(*conditions)
            .order_by(ordered, ProjectFinanceInboxORM.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        return FinancePageFacts(
            items=tuple(self._fact(row) for row in rows),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=direction,
        )

    @staticmethod
    def _fact(row: ProjectFinanceInboxORM) -> ApprovedTimePostingFailureFact:
        code = str(row.last_error_code or row.quarantine_reason_code or "DELIVERY_PENDING")
        return ApprovedTimePostingFailureFact(
            id=row.id,
            event_id=row.event_id,
            source_id=row.aggregate_id,
            source_revision=int(row.source_revision or row.aggregate_version),
            resource_id=str(row.source_resource_id or ""),
            work_date=row.source_work_date,
            status=row.status,
            failure_code=code,
            failure_message=str(row.last_error_message or "Delivery is awaiting processing."),
            failure_category=_failure_category(code),
            corrective_action=_corrective_action(code, row.status),
            attempt_count=row.attempt_count,
            max_attempts=row.max_attempts,
            retryable=row.status in {"processing", "retry"},
            updated_at=row.updated_at,
        )


__all__ = ["SqlAlchemyFinanceIntegrationReader"]
