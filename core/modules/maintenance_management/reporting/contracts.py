from __future__ import annotations

from dataclasses import dataclass

from core.platform.report_runtime import ReportFormat


@dataclass(frozen=True)
class MaintenanceReportContract:
    report_key: str
    label: str
    description: str
    supported_formats: tuple[ReportFormat, ...]
    permission_code: str = "report.export"
    module_code: str = "maintenance_management"


MAINTENANCE_REPORT_CONTRACTS: tuple[MaintenanceReportContract, ...] = (
    MaintenanceReportContract(
        report_key="maintenance_backlog_excel",
        label="Maintenance Backlog Excel",
        description="Planner-facing backlog summary for due, overdue, and constrained work.",
        supported_formats=("excel",),
    ),
    MaintenanceReportContract(
        report_key="maintenance_backlog_pdf",
        label="Maintenance Backlog PDF",
        description="Shareable backlog summary for weekly operational review.",
        supported_formats=("pdf",),
    ),
    MaintenanceReportContract(
        report_key="maintenance_pm_compliance_excel",
        label="PM Compliance Excel",
        description="Preventive maintenance compliance workbook for audit and operations review.",
        supported_formats=("excel",),
    ),
    MaintenanceReportContract(
        report_key="maintenance_pm_compliance_pdf",
        label="PM Compliance PDF",
        description="Preventive compliance narrative summary for distribution.",
        supported_formats=("pdf",),
    ),
    MaintenanceReportContract(
        report_key="maintenance_downtime_excel",
        label="Downtime Excel",
        description="Downtime event and asset-impact workbook for reliability analysis.",
        supported_formats=("excel",),
    ),
    MaintenanceReportContract(
        report_key="maintenance_downtime_pdf",
        label="Downtime PDF",
        description="Downtime summary report for management and incident review packs.",
        supported_formats=("pdf",),
    ),
    MaintenanceReportContract(
        report_key="maintenance_execution_overview_excel",
        label="Execution Overview Excel",
        description="Execution throughput, labor, and closeout workbook for supervisors.",
        supported_formats=("excel",),
    ),
    MaintenanceReportContract(
        report_key="maintenance_execution_overview_pdf",
        label="Execution Overview PDF",
        description="Execution summary report for shift and weekly governance reviews.",
        supported_formats=("pdf",),
    ),
    MaintenanceReportContract(
        report_key="maintenance_recurring_failures_excel",
        label="Recurring Failures Excel",
        description="Recurring-failure workbook for reliability-engineer review and follow-up actions.",
        supported_formats=("excel",),
    ),
    MaintenanceReportContract(
        report_key="maintenance_exception_review_excel",
        label="Exception Review Excel",
        description="Open sensor and integration exception workbook for reliability exception review.",
        supported_formats=("excel",),
    ),
)


__all__ = [
    "MAINTENANCE_REPORT_CONTRACTS",
    "MaintenanceReportContract",
]
