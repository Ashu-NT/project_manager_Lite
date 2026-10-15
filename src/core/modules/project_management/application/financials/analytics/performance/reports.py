from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.reads.financials.performance.models.performance_facts import (
    PerformanceReportDefinitionFact,
    PerformanceReportsFacts,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)

if TYPE_CHECKING:
    from src.core.modules.project_management.contracts.reads.financials.overview.models.overview_facts import (
        FinanceOverviewFacts,
    )
    from src.core.platform.domain.security.auth.session import UserSessionContext

logger = logging.getLogger(__name__)


class ReportsQueries:
    # Host attributes supplied by ``ProjectFinancePerformanceQuery`` (declared for type checking only).
    _user_session: UserSessionContext | None
    _authorize_finance: Callable[[str, str], None]
    _read_basis: Callable[[str, date], FinanceOverviewFacts]

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
        resolved_as_of = as_of_date or datetime.now(UTC).astimezone().date()
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
