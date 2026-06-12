from __future__ import annotations


def serialize_audit_entries_for_activity(
    entries: object,
    entity_id: str,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for entry in entries:
        if getattr(entry, "entity_id", None) != entity_id:
            continue
        action = getattr(entry, "action", "") or ""
        details = getattr(entry, "details_label", "") or action
        actor = getattr(entry, "actor_username", "") or ""
        title = f"{details} — {actor}" if actor else details
        meta = str(getattr(entry, "occurred_at", "") or "")
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
