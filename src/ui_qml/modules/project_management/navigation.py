from __future__ import annotations

from dataclasses import dataclass


PM_CANONICAL_ROUTE_ID = "project_management.workspace"


@dataclass(frozen=True, slots=True)
class PMWorkspaceIntent:
    destination_id: str
    workspace_key: str
    secondary_id: str = ""


_INTENT_BY_WORKSPACE_KEY: dict[str, PMWorkspaceIntent] = {
    "dashboard": PMWorkspaceIntent("overview", "dashboard"),
    "portfolio": PMWorkspaceIntent("portfolio", "portfolio"),
    "projects": PMWorkspaceIntent("work", "projects", "projects"),
    "tasks": PMWorkspaceIntent("work", "tasks", "tasks"),
    "scheduling": PMWorkspaceIntent("work", "scheduling", "planning"),
    "resources": PMWorkspaceIntent("workload", "resources", "resources"),
    "timesheets": PMWorkspaceIntent("workload", "timesheets", "review_queue"),
    "financials": PMWorkspaceIntent("finance", "financials"),
    "register": PMWorkspaceIntent("governance", "register", "register"),
    "collaboration": PMWorkspaceIntent("governance", "collaboration", "collaboration"),
}

PM_WORKSPACE_KEYS = tuple(_INTENT_BY_WORKSPACE_KEY)
PM_COMPATIBILITY_ROUTE_IDS = tuple(
    f"project_management.{workspace_key}" for workspace_key in PM_WORKSPACE_KEYS
)


def workspace_intent(workspace_key: object) -> PMWorkspaceIntent | None:
    return _INTENT_BY_WORKSPACE_KEY.get(str(workspace_key or "").strip())


def compatibility_route_intent(route_id: object) -> PMWorkspaceIntent | None:
    normalized = str(route_id or "").strip()
    prefix = "project_management."
    if not normalized.startswith(prefix) or normalized == PM_CANONICAL_ROUTE_ID:
        return None
    return workspace_intent(normalized[len(prefix) :])


__all__ = [
    "PM_CANONICAL_ROUTE_ID",
    "PM_COMPATIBILITY_ROUTE_IDS",
    "PM_WORKSPACE_KEYS",
    "PMWorkspaceIntent",
    "compatibility_route_intent",
    "workspace_intent",
]
