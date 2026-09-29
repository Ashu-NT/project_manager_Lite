from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.core.modules.project_management.application.dashboard.models.report_models import (
    GanttTaskBar,
    ProjectKPI,
    ResourceLoadRow,
)
from src.core.modules.project_management.application.financials import (
    FinanceSnapshot,
    ProjectFinanceLedgerRow,
)
from src.core.modules.project_management.application.financials.models import (
    CostSourceBreakdown,
)

MAX_PROJECT_FINANCE_LEDGER_EXPORT_ROWS = 500


@dataclass(frozen=True)
class ProjectFinanceLedgerExportPage:
    rows: tuple[ProjectFinanceLedgerRow, ...]
    offset: int
    limit: int
    total: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.rows) < self.total

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
    project_finance_ledger_page: ProjectFinanceLedgerExportPage | None
    as_of: date
    generated_at: datetime

@dataclass
class ExcelReportContext(ReportExportContext):
    gantt: list[GanttTaskBar]

@dataclass
class PdfReportContext(ReportExportContext):
    gantt_png_path: str


__all__ = [
    "MAX_PROJECT_FINANCE_LEDGER_EXPORT_ROWS",
    "EvmContext",
    "ExcelReportContext",
    "ProjectFinanceLedgerExportPage",
    "GanttContext",
    "PdfReportContext",
    "ReportExportContext",
]
