from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationRecordViewModel,
)


def sort_records_by_created_desc(
    view_models: tuple[CollaborationRecordViewModel, ...],
) -> tuple[CollaborationRecordViewModel, ...]:
    return tuple(
        sorted(
            view_models,
            key=lambda item: str(item.state.get("createdAt") or ""),
            reverse=True,
        )
    )
