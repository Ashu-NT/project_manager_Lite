from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    CostSourceBreakdown,
    GanttTaskBar,
    ProjectKPI,
    ResourceLoadRow,
)
from src.core.modules.project_management.application.financials import (
    FinanceLedgerRow,
    FinanceSnapshot,
)


MAX_FINANCE_LEDGER_EXPORT_ROWS = 500


@dataclass(frozen=True)
class FinanceLedgerExportPage:
    rows: tuple[FinanceLedgerRow, ...]
    offset: int
    limit: int
    total: int

    @classmethod
    def build(
        cls,
        rows: list[FinanceLedgerRow],
        *,
        offset: int,
        limit: int,
    ) -> "FinanceLedgerExportPage":
        if offset < 0:
            raise ValueError("Finance ledger export offset must be non-negative.")
        if limit < 1 or limit > MAX_FINANCE_LEDGER_EXPORT_ROWS:
            raise ValueError(
                "Finance ledger export limit must be between 1 and "
                f"{MAX_FINANCE_LEDGER_EXPORT_ROWS}."
            )
        return cls(
            rows=tuple(rows[offset : offset + limit]),
            offset=offset,
            limit=limit,
            total=len(rows),
        )

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
    finance_ledger_page: FinanceLedgerExportPage | None
    as_of: date
    generated_at: datetime

@dataclass
class ExcelReportContext(ReportExportContext):
    gantt: list[GanttTaskBar]

@dataclass
class PdfReportContext(ReportExportContext):
    gantt_png_path: str


__all__ = [
    "ExcelReportContext",
    "EvmContext",
    "FinanceLedgerExportPage",
    "GanttContext",
    "MAX_FINANCE_LEDGER_EXPORT_ROWS",
    "PdfReportContext",
    "ReportExportContext",
]
