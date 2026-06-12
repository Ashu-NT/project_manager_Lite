from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.work_requests import (
    MaintenanceWorkRequestOptionViewModel,
)


def option(value: str, label: str) -> MaintenanceWorkRequestOptionViewModel:
    return MaintenanceWorkRequestOptionViewModel(value=value, label=label)
