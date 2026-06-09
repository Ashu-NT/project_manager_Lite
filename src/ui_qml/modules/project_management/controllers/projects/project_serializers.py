from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_project_record_view_models,
)


def serialize_project_section(section) -> dict[str, object]:
    return {
        "title": section.title,
        "subtitle": section.subtitle,
        "emptyState": section.empty_state,
        "items": serialize_project_record_view_models(section.items),
    }


__all__ = ["serialize_project_section"]
