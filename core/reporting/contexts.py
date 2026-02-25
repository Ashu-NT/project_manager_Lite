from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from core.services.reporting import (
    CostSourceBreakdown,
    GanttTaskBar,
    ProjectKPI,
    ResourceLoadRow,
)
from core.services.finance.models import FinanceSnapshot

@dataclass
class GanttContext:
    bars: List[GanttTaskBar]
    today: date

@dataclass
class EvmContext:
    series: list
    as_of: date

@dataclass
class ReportExportContext:
    kpi: ProjectKPI
    resources: List[ResourceLoadRow]
    evm: Optional[object]
    evm_series: Optional[list]
    baseline_variance: Optional[list]
    cost_breakdown: Optional[list]
    cost_sources: Optional[CostSourceBreakdown]
    finance_snapshot: Optional[FinanceSnapshot]
    as_of: date

@dataclass
class ExcelReportContext(ReportExportContext):
    gantt: List[GanttTaskBar]

@dataclass
class PdfReportContext(ReportExportContext):
    gantt_png_path: str

