from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaintenanceExportContract:
    operation_key: str
    label: str
    description: str
    artifact_format: str
    permission_code: str = "report.export"
    module_code: str = "maintenance_management"


MAINTENANCE_EXPORT_CONTRACTS: tuple[MaintenanceExportContract, ...] = (
    MaintenanceExportContract(
        operation_key="maintenance_asset_register_csv",
        label="Asset Register CSV",
        description="Tabular asset register extract for rollout validation and downstream integrations.",
        artifact_format="csv",
    ),
    MaintenanceExportContract(
        operation_key="maintenance_asset_register_excel",
        label="Asset Register Excel",
        description="Workbook asset register export for planners and reliability teams.",
        artifact_format="excel",
    ),
    MaintenanceExportContract(
        operation_key="maintenance_preventive_plan_library_csv",
        label="Preventive Plan Library CSV",
        description="Preventive plan and template extract for audit and review.",
        artifact_format="csv",
    ),
    MaintenanceExportContract(
        operation_key="maintenance_preventive_plan_library_excel",
        label="Preventive Plan Library Excel",
        description="Workbook export of preventive plan and template structure.",
        artifact_format="excel",
    ),
    MaintenanceExportContract(
        operation_key="maintenance_work_order_backlog_csv",
        label="Work Order Backlog CSV",
        description="Open work backlog extract for scheduling and planning.",
        artifact_format="csv",
    ),
    MaintenanceExportContract(
        operation_key="maintenance_work_order_backlog_excel",
        label="Work Order Backlog Excel",
        description="Workbook backlog extract for planning boards and execution review.",
        artifact_format="excel",
    ),
    MaintenanceExportContract(
        operation_key="maintenance_material_readiness_csv",
        label="Material Readiness CSV",
        description="Cross-module material readiness and shortage extract for maintenance planning.",
        artifact_format="csv",
    ),
    MaintenanceExportContract(
        operation_key="maintenance_material_readiness_excel",
        label="Material Readiness Excel",
        description="Workbook material readiness extract across work, reservations, and procurement.",
        artifact_format="excel",
    ),
    MaintenanceExportContract(
        operation_key="maintenance_document_link_register_csv",
        label="Document Link Register CSV",
        description="Linked-document register for maintenance assets, plans, and execution evidence.",
        artifact_format="csv",
    ),
    MaintenanceExportContract(
        operation_key="maintenance_document_link_register_excel",
        label="Document Link Register Excel",
        description="Workbook linked-document register for audits and handover packs.",
        artifact_format="excel",
    ),
)


__all__ = [
    "MAINTENANCE_EXPORT_CONTRACTS",
    "MaintenanceExportContract",
]
