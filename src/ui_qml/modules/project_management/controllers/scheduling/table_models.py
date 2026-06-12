from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject

from src.ui_qml.shared.models.data_table_model import DynamicTableModel


@dataclass
class SchedulingTableModels:
    schedule: DynamicTableModel
    schedule_impact_tasks: DynamicTableModel
    dependency: DynamicTableModel
    constraint: DynamicTableModel
    calendar_summary: DynamicTableModel
    baseline_variance: DynamicTableModel
    diagnostics: DynamicTableModel
    violations: DynamicTableModel
    resources_loading: DynamicTableModel
    baseline_compare: DynamicTableModel
    baseline_register: DynamicTableModel
    delayed: DynamicTableModel
    holiday: DynamicTableModel


def create_scheduling_table_models(parent: QObject) -> SchedulingTableModels:
    return SchedulingTableModels(
        schedule=DynamicTableModel(parent),
        schedule_impact_tasks=DynamicTableModel(parent),
        dependency=DynamicTableModel(parent),
        constraint=DynamicTableModel(parent),
        calendar_summary=DynamicTableModel(parent),
        baseline_variance=DynamicTableModel(parent),
        diagnostics=DynamicTableModel(parent),
        violations=DynamicTableModel(parent),
        resources_loading=DynamicTableModel(parent),
        baseline_compare=DynamicTableModel(parent),
        baseline_register=DynamicTableModel(parent),
        delayed=DynamicTableModel(parent),
        holiday=DynamicTableModel(parent),
    )


__all__ = ["SchedulingTableModels", "create_scheduling_table_models"]
