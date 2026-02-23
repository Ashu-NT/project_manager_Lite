"""Facade module for report dialogs.

This keeps legacy imports stable while each dialog implementation lives
in its own module for better maintainability.
"""

from ui.report.dialog_critical_path import CriticalPathDialog
from ui.report.dialog_gantt import GanttPreviewDialog
from ui.report.dialog_kpi import KPIReportDialog
from ui.report.dialog_resource_load import ResourceLoadDialog

__all__ = [
    "KPIReportDialog",
    "GanttPreviewDialog",
    "CriticalPathDialog",
    "ResourceLoadDialog",
]

