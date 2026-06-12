from __future__ import annotations

from dataclasses import dataclass

from src.ui_qml.shared.models.data_table_model import DynamicTableModel


@dataclass
class ProjectTableModels:
    projects: DynamicTableModel
    project_tasks: DynamicTableModel
    project_resources: DynamicTableModel


def create_project_table_models(parent) -> ProjectTableModels:
    return ProjectTableModels(
        projects=DynamicTableModel(parent),
        project_tasks=DynamicTableModel(parent),
        project_resources=DynamicTableModel(parent),
    )


__all__ = ["ProjectTableModels", "create_project_table_models"]
