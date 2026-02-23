from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from core.services.reporting_models import (
    GanttTaskBar,
    ProjectKPI,
    ResourceLoadRow,
)

@dataclass
class GanttContext:
    bars: List[GanttTaskBar]
    today: date

@dataclass
class EvmContext:
    series: list
    as_of: date

@dataclass
class ExcelReportContext:
    kpi: ProjectKPI
    gantt: List[GanttTaskBar]
    resources: List[ResourceLoadRow]
    evm: Optional[object]
    evm_series: Optional[list]
    baseline_variance: Optional[list]
    cost_breakdown: Optional[list]
    as_of: date

@dataclass
class PdfReportContext:
    kpi: ProjectKPI
    gantt_png_path: str
    resources: List[ResourceLoadRow]
    evm: Optional[object]
    evm_series: Optional[list]
    baseline_variance: Optional[list]
    cost_breakdown: Optional[list]
    as_of: date
