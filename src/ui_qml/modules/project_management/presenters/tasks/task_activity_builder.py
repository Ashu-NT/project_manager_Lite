from __future__ import annotations

from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.ui_qml.modules.project_management.presenters.common.activity_log_builder import (
    build_activity_records,
    build_actor_lookup,
)
from src.ui_qml.shared.models.activity_item import serialize_activity_items


def build_task_activity_page(
    page,
    *,
    user_api: PlatformUserDesktopApi | None = None,
    employee_api: PlatformEmployeeDesktopApi | None = None,
) -> dict[str, object]:
    actor_lookup = build_actor_lookup(
        user_api.list_users() if user_api is not None else DesktopApiResult(ok=False),
        employee_api.list_employees() if employee_api is not None else None,
    )
    items = build_activity_records(
        page.items,
        actor_lookup=actor_lookup,
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
