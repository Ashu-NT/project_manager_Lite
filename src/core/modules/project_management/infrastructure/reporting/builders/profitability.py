"""Reporting boundary: authorization and one resolved date, then canonical query."""

from __future__ import annotations

from datetime import date, datetime, timezone

from src.core.modules.project_management.application.financials.models.finance_models import (
    ProjectCommercialProjection,
)
from src.core.modules.project_management.application.financials.revenue.commercial_projection_query import (
    CommercialProjectionQuery,
)
from src.core.platform.common.exceptions import NotFoundError


class ReportingProfitabilityMixin:
    def get_project_commercial_projection(
        self, project_id: str, *, as_of_date: date | None = None,
    ) -> ProjectCommercialProjection:
        self._require_finance_view("view project commercial projection", project_id=project_id)
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view commercial projection"
        )
        return CommercialProjectionQuery(
            billing_repo=self._billing_repo,
            financial_profile_repo=self._financial_profile_repo,
            billing_reader=self._billing_reader,
            cost_totals=lambda project, cutoff: self._compose_finance_policy(project, as_of=cutoff)[1].totals,
        ).read(
            tenant_id=scope.tenant_id, organization_id=scope.organization_id,
            project_id=project_id,
            as_of_date=as_of_date or datetime.now(timezone.utc).astimezone().date(),
            include_profitability=self._has_profitability_view(project_id),
        )


__all__ = ["ReportingProfitabilityMixin"]
