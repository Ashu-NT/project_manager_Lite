from __future__ import annotations


def serialize_activity_entries(
    entries: object,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for entry in entries:
        action = getattr(entry, "action", "") or ""
        details = getattr(entry, "human_message", "") or action
        actor = getattr(entry, "actor_id", "") or ""
        title = f"{details} — {actor}" if actor else details
        meta = str(getattr(entry, "timestamp", "") or "")
        al = action.lower()
        if any(k in al for k in ("creat", "add", "open", "approv", "complet", "receiv")):
            status = "success"
        elif any(k in al for k in ("delet", "cancel", "reject", "close", "remov")):
            status = "danger"
        elif any(k in al for k in ("updat", "edit", "modif", "submit", "post", "transfer", "issue", "return", "adjust")):
            status = "warning"
        else:
            status = ""
        items.append({"title": title, "metaText": meta, "statusLabel": status, "routeId": ""})
    return items
