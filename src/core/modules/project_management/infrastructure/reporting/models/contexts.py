from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    CostSourceBreakdown,
    GanttTaskBar,
    ProjectKPI,
    ResourceLoadRow,
)
from src.core.modules.project_management.application.financials import FinanceSnapshot

@dataclass
class GanttContext:
    bars: list[GanttTaskBar]
    today: date

@dataclass
class EvmContext:
    series: list
    as_of: date

@dataclass
class ReportExportContext:
    kpi: ProjectKPI
    resources: list[ResourceLoadRow]
    evm: object | None
    evm_series: list | None
    baseline_variance: list | None
    cost_breakdown: list | None
    cost_sources: CostSourceBreakdown | None
    finance_snapshot: FinanceSnapshot | None
    as_of: date

@dataclass
class ExcelReportContext(ReportExportContext):
    gantt: list[GanttTaskBar]

@dataclass
class PdfReportContext(ReportExportContext):
    gantt_png_path: str
