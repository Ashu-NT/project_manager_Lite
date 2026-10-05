from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    PerformanceReportDefinitionFact,
    PerformanceReportsFacts,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)

logger = logging.getLogger(__name__)


class ReportsQueries:
    def get_reports(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
    ) -> PerformanceReportsFacts:
        require_permission(
            self._user_session,
            "report.view",
            operation_label="view project finance reports",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "report.view",
            operation_label="view project finance reports",
        )
        self._authorize_finance(project_id, "view project finance report basis")
        resolved_as_of = as_of_date or datetime.now(timezone.utc).astimezone().date()
        basis = self._read_basis(project_id, resolved_as_of)
        return PerformanceReportsFacts(
            project_id=project_id,
            as_of_date=resolved_as_of,
            currency_code=basis.currency_code,
            budget_revision=basis.approved_budget_revision,
            forecast_revision=basis.approved_forecast_revision,
            forecast_as_of=basis.approved_forecast_as_of,
            definitions=(
                PerformanceReportDefinitionFact(
                    report_code="project_finance_xlsx",
                    display_name="Project Finance Workbook",
                    formats=("xlsx",),
                    authority_label="Authoritative Finance reads with permission-filtered report sections",
                ),
                PerformanceReportDefinitionFact(
                    report_code="project_finance_pdf",
                    display_name="Project Finance Report",
                    formats=("pdf",),
                    authority_label="Authoritative Finance reads with permission-filtered report sections",
                ),
            ),
        )
