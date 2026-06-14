from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    serialize_activity_entries,
)


def load_detail_activity(ctrl, entity_id: str, entity_type: str) -> None:
    if ctrl._activity_api is None or not entity_id:
        ctrl._set_detail_activity_items([])
        return
    try:
        result = ctrl._activity_api.list_recent(
            entity_type=entity_type, entity_id=entity_id, limit=200
        )
        items = (
            serialize_activity_entries(result.data)
            if result.ok and result.data is not None
            else []
        )
    except Exception:  # pragma: no cover - defensive fallback
        items = []
    ctrl._set_detail_activity_items(items)
