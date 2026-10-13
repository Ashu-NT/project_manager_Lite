from __future__ import annotations

import logging
from datetime import date

from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    CostPhasingFacts,
    CostPhasingQuery,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError

logger = logging.getLogger(__name__)


class CostPhasingQueries:
    def get_cost_phasing(
        self,
        project_id: str,
        *,
        date_from: date,
        date_to: date,
        granularity: str = "month",
        as_of_date: date | None = None,
    ) -> CostPhasingFacts:
        self._authorize_finance(project_id, "view project cost phasing")
        normalized_granularity = str(granularity or "").strip().lower()
        if normalized_granularity not in {"month", "quarter"}:
            raise BusinessRuleError(
                "Cost Phasing granularity must be month or quarter.",
                code="COST_PHASING_GRANULARITY_INVALID",
            )
        if date_from > date_to:
            raise BusinessRuleError(
                "Cost Phasing start date must not be after its end date.",
                code="COST_PHASING_RANGE_INVALID",
            )
        month_span = (date_to.year - date_from.year) * 12 + date_to.month - date_from.month
        if month_span > 36:
            raise BusinessRuleError(
                "Cost Phasing range cannot exceed 36 months.",
                code="COST_PHASING_RANGE_TOO_LARGE",
            )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project cost phasing"
        )
        facts = self._performance_reader.read_cost_phasing(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            query=CostPhasingQuery(
                date_from=date_from,
                date_to=date_to,
                granularity=normalized_granularity,
                as_of_date=as_of_date,
            ),
        )
        if facts is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        return facts
