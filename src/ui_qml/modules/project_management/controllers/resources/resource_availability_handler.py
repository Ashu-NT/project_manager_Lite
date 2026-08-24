from __future__ import annotations

from datetime import date, timedelta

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_resource_availability_view_model,
)
from src.ui_qml.modules.project_management.controllers.resources.resource_state import (
    default_resource_availability,
)


def load_resource_availability(
    controller,
    start_date: str = "",
    end_date: str = "",
) -> None:
    resource_id = str(controller._selected_resource_id or "").strip()
    if not resource_id:
        controller._set_resource_availability(default_resource_availability())
        return
    resolved_start = start_date.strip() or date.today().isoformat()
    resolved_end = end_date.strip() or (date.today() + timedelta(days=30)).isoformat()
    controller._clear_section_error("availability")
    controller._set_is_busy(True)
    try:
        view_model = controller._resources_workspace_presenter.build_resource_availability(
            resource_id,
            start_date=resolved_start,
            end_date=resolved_end,
        )
        controller._set_resource_availability(
            serialize_resource_availability_view_model(view_model)
        )
    except Exception as exc:
        controller._set_resource_availability(default_resource_availability())
        controller._set_section_error("availability", str(exc))
    finally:
        controller._set_is_busy(False)


__all__ = ["load_resource_availability"]
