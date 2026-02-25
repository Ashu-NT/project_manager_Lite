"""Facade module for report dialogs.

This keeps legacy imports stable while each dialog implementation lives
in its own module for better maintainability.
"""

from ui.report.dialog_critical_path import CriticalPathDialog
from ui.report.dialog_baseline_compare import BaselineCompareDialog
from ui.report.dialog_evm import EvmReportDialog
from ui.report.dialog_gantt import GanttPreviewDialog
from ui.report.dialog_kpi import KPIReportDialog
from ui.report.dialog_finance import FinanceReportDialog
from ui.report.dialog_performance import PerformanceVarianceDialog
from ui.report.dialog_resource_load import ResourceLoadDialog

__all__ = [
    "KPIReportDialog",
    "GanttPreviewDialog",
    "CriticalPathDialog",
    "BaselineCompareDialog",
    "ResourceLoadDialog",
    "FinanceReportDialog",
    "EvmReportDialog",
    "PerformanceVarianceDialog",
]
