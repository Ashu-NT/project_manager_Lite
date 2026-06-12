from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.work_orders import (
    MaintenanceWorkOrderOptionViewModel,
)


def option(value: str, label: str) -> MaintenanceWorkOrderOptionViewModel:
    return MaintenanceWorkOrderOptionViewModel(value=value, label=label)


SOURCE_TYPE_OPTIONS = (
    option("MANUAL", "Manual"),
    option("WORK_REQUEST", "Work Request"),
)
