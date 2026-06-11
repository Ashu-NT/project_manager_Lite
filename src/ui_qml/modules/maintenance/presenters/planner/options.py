from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerOptionViewModel,
)


def option(value: str, label: str) -> MaintenancePlannerOptionViewModel:
    return MaintenancePlannerOptionViewModel(value=value, label=label)
