from __future__ import annotations

from src.core.modules.project_management.application.financials.analytics.performance.dto.responses.reports import (
    FinancialReportsDto,
)
from src.core.modules.project_management.contracts.reads.financials.performance.models.performance_facts import (
    PerformanceReportDefinitionFact,
    PerformanceReportsFacts,
)


def serialize_performance_reports(facts: PerformanceReportsFacts) -> FinancialReportsDto:
    return FinancialReportsDto(
        project_id=facts.project_id,
        as_of_date=facts.as_of_date,
        currency_code=facts.currency_code,
        budget_revision=facts.budget_revision,
        forecast_revision=facts.forecast_revision,
        forecast_as_of=facts.forecast_as_of,
        definitions=tuple(
            PerformanceReportDefinitionFact(
                report_code=item.report_code,
                display_name=item.display_name,
                formats=item.formats,
                authority_label=item.authority_label,
                requires_sensitive_finance=item.requires_sensitive_finance,
                requires_profitability=item.requires_profitability,
            )
            for item in facts.definitions
        ),
    )
