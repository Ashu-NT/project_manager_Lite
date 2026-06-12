from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    serialize_audit_entries_for_activity,
)


def load_detail_activity(ctrl, entity_id: str, entity_type: str) -> None:
    if ctrl._platform_audit is None or not entity_id:
        ctrl._set_detail_activity_items([])
        return
    try:
        result = ctrl._platform_audit.list_recent(
            entity_type=entity_type, limit=200
        )
        items = (
            serialize_audit_entries_for_activity(result.data, entity_id)
            if result.ok and result.data is not None
            else []
        )
    except Exception:  # pragma: no cover - defensive fallback
        items = []
    ctrl._set_detail_activity_items(items)
