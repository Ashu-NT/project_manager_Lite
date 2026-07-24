from __future__ import annotations


def rebuild_panel_item_index(controller) -> None:
    controller._panel_item_index = {}
    panel_map = {
        "inbox": controller._notifications,
        "mentions": controller._mentions,
        "approvals": controller._approvals,
        "activity": controller._activity_feed,
        "team_updates": controller._team_updates,
    }
    for pid, panel in panel_map.items():
        controller._panel_item_index[pid] = {
            str(item.get("id") or ""): dict(item)
            for item in panel.get("items", [])
        }


def item_for_panel(
    controller, panel_id: str, item_id: str
) -> dict[str, object] | None:
    return controller._panel_item_index.get(str(panel_id or ""), {}).get(
        str(item_id or "")
    )


__all__ = ["item_for_panel", "rebuild_panel_item_index"]
