from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.reliability import (
    MaintenanceReliabilityRecurringRowViewModel,
)


def recurring_row(row) -> MaintenanceReliabilityRecurringRowViewModel:
    return MaintenanceReliabilityRecurringRowViewModel(
        anchor_label=row.anchor_label,
        failure_name=row.failure_name,
        leading_root_cause_name=row.leading_root_cause_name,
        occurrence_count=row.occurrence_count,
        open_work_orders=row.open_work_orders,
        mean_interval_hours_label=row.mean_interval_hours_label,
    )
