from __future__ import annotations

def set_resource_bulk_selection(controller, resource_id: str, selected: bool) -> None:
    normalized_id = (resource_id or "").strip()
    if not normalized_id:
        return
    current = list(controller._selected_resource_ids)
    if selected and normalized_id not in current:
        current.append(normalized_id)
    elif not selected and normalized_id in current:
        current.remove(normalized_id)
    else:
        return
    controller._set_selected_resource_ids(current)


def clear_resource_bulk_selection(controller) -> None:
    controller._set_selected_resource_ids([])


def select_visible_resources(controller) -> None:
    items = controller._resources.get("items") or []
    visible_ids = [
        str(item.get("id", "") or "")
        for item in items
        if item.get("id")
    ]
    controller._set_selected_resource_ids(visible_ids)


__all__ = [
    "clear_resource_bulk_selection",
    "select_visible_resources",
    "set_resource_bulk_selection",
]
