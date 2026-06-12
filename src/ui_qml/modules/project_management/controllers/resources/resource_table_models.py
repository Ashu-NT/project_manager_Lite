from __future__ import annotations

from dataclasses import dataclass

from src.ui_qml.shared.models.data_table_model import DynamicTableModel


@dataclass
class ResourceTableModels:
    resources: DynamicTableModel
    resource_skills: DynamicTableModel
    resource_certifications: DynamicTableModel
    resource_assignments: DynamicTableModel


def create_resource_table_models(parent) -> ResourceTableModels:
    return ResourceTableModels(
        resources=DynamicTableModel(parent),
        resource_skills=DynamicTableModel(parent),
        resource_certifications=DynamicTableModel(parent),
        resource_assignments=DynamicTableModel(parent),
    )


__all__ = ["ResourceTableModels", "create_resource_table_models"]
