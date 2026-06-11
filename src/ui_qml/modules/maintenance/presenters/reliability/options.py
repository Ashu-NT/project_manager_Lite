from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.reliability import (
    MaintenanceReliabilityOptionViewModel,
)


def option(value: str, label: str) -> MaintenanceReliabilityOptionViewModel:
    return MaintenanceReliabilityOptionViewModel(value=value, label=label)
