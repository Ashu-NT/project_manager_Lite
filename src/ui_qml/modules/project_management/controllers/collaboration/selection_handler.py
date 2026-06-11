from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_collaboration_detail_view_model,
)
from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationDetailViewModel,
)

from .detail_builder import build_detail_payload
from .panel_index_service import item_for_panel


def _empty_item_detail() -> dict[str, object]:
    return serialize_collaboration_detail_view_model(
        CollaborationDetailViewModel(
            id="", title="", status_label="", subtitle="", description=""
        )
    )


def select_item(controller, panel_id: str, item_id: str) -> None:
    item = item_for_panel(controller, panel_id, item_id)
    if item is None:
        controller._set_selected_item_detail(_empty_item_detail())
        return
    controller._set_selected_item_detail(
        build_detail_payload(panel_id, item, controller._panel_item_index)
    )


def clear_selection(controller) -> None:
    controller._set_selected_item_detail(_empty_item_detail())


def route_for_item(controller, panel_id: str, item_id: str) -> str:
    item = item_for_panel(controller, panel_id, item_id)
    if item is None:
        return ""
    return str(item.get("state", {}).get("routeId") or "")


__all__ = ["clear_selection", "route_for_item", "select_item"]
