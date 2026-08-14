from __future__ import annotations

from .labels import title_case


def build_inbox_rows(collection: dict[str, object]) -> list[dict]:
    return [
        {
            "id": item.get("id"),
            "title": str(item.get("title") or ""),
            "workflowType": "Mention",
            "projectName": str((item.get("state") or {}).get("projectName") or ""),
            "supportingText": str(item.get("supportingText") or ""),
            "statusLabel": str(item.get("statusLabel") or ""),
            "subtitle": str(item.get("subtitle") or ""),
            "metaText": str(item.get("metaText") or ""),
            "state": dict(item.get("state") or {}),
        }
        for item in collection.get("items", [])
    ]


def build_mentions_rows(collection: dict[str, object]) -> list[dict]:
    result = []
    for item in collection.get("items", []):
        state = item.get("state") or {}
        actor = state.get("actorUsername") or ""
        result.append(
            {
                "id": item.get("id"),
                "title": str(item.get("title") or ""),
                "sourceName": str(state.get("taskId") or item.get("subtitle") or ""),
                "actorLabel": ("@" + actor) if actor else "",
                "metaText": str(item.get("metaText") or ""),
                "statusLabel": str(item.get("statusLabel") or ""),
                "subtitle": str(item.get("subtitle") or ""),
                "supportingText": str(item.get("supportingText") or ""),
                "state": dict(state),
            }
        )
    return result


def build_approvals_rows(collection: dict[str, object]) -> list[dict]:
    result = []
    for item in collection.get("items", []):
        state = item.get("state") or {}
        requestor = state.get("requestor") or ""
        result.append(
            {
                "id": item.get("id"),
                "title": str(item.get("title") or ""),
                "approvalType": title_case(
                    state.get("requestType") or state.get("entityType") or "approval"
                ),
                "requestor": ("@" + requestor) if requestor else "",
                "moduleLabel": str(state.get("moduleLabel") or ""),
                "statusLabel": str(item.get("statusLabel") or ""),
                "subtitle": str(item.get("subtitle") or ""),
                "supportingText": str(item.get("supportingText") or ""),
                "metaText": str(item.get("metaText") or ""),
                "state": dict(state),
            }
        )
    return result


__all__ = ["build_approvals_rows", "build_inbox_rows", "build_mentions_rows"]
