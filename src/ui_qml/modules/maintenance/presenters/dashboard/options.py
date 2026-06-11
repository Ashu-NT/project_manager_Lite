from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.dashboard import MaintenanceOptionViewModel


def option(value: str, label: str) -> MaintenanceOptionViewModel:
    return MaintenanceOptionViewModel(value=value, label=label)
