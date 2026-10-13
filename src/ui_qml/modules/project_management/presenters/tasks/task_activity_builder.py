from __future__ import annotations

from src.ui_qml.modules.project_management.presenters.common.activity_log_builder import (
    build_activity_records,
)
from src.ui_qml.shared.models.activity_item import serialize_activity_items


def build_task_activity_page(
    page,
) -> dict[str, object]:
    items = build_activity_records(
        page.items,
        field_labels={},
    )
    return {
        "items": serialize_activity_items(items),
        "total": page.filtered_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort_key,
        "sortDirection": page.sort_direction,
    }


__all__ = ["build_task_activity_page"]
