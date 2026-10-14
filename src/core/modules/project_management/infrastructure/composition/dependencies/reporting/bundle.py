from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.reporting import (
    BaselineCompareReportBuilder,
    CostBreakdownReportBuilder,
    EarnedValueReportBuilder,
    LaborReportBuilder,
    ProfitabilityReportBuilder,
    ProjectKpiReportBuilder,
    ScheduleVarianceReportBuilder,
)


@dataclass(frozen=True)
class ReportingComposition:
    kpi: ProjectKpiReportBuilder
    earned_value: EarnedValueReportBuilder
    cost_breakdown: CostBreakdownReportBuilder
    baseline_compare: BaselineCompareReportBuilder
    schedule_variance: ScheduleVarianceReportBuilder
    profitability: ProfitabilityReportBuilder
    labor: LaborReportBuilder
