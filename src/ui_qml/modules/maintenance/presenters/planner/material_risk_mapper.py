from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerMaterialRiskRowViewModel,
)


def material_risk_row(row) -> MaintenancePlannerMaterialRiskRowViewModel:
    return MaintenancePlannerMaterialRiskRowViewModel(
        id=row.id,
        work_order_id=row.work_order_id,
        work_order_label=row.work_order_label,
        material_label=row.material_label,
        procurement_status_label=row.procurement_status_label,
        quantity_label=row.quantity_label,
        storeroom_label=row.storeroom_label,
    )
