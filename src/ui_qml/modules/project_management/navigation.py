from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


PM_CANONICAL_ROUTE_ID = "project_management.workspace"


class ProjectContextPolicy(str, Enum):
    """Whether a PM destination needs the shared active-project context.
    Lives on destination/navigation metadata, not on the project-context
    controller itself, so the state owner (PMProjectContextController)
    stays free of per-destination navigation semantics -- see R2.2."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class PMWorkspaceIntent:
    destination_id: str
    workspace_key: str
    secondary_id: str = ""
    project_context_policy: ProjectContextPolicy = ProjectContextPolicy.OPTIONAL


_INTENT_BY_WORKSPACE_KEY: dict[str, PMWorkspaceIntent] = {
    "dashboard": PMWorkspaceIntent(
        "overview", "dashboard", project_context_policy=ProjectContextPolicy.OPTIONAL
    ),
    "portfolio": PMWorkspaceIntent(
        "portfolio", "portfolio", project_context_policy=ProjectContextPolicy.NOT_APPLICABLE
    ),
    "projects": PMWorkspaceIntent(
        "work", "projects", "projects", project_context_policy=ProjectContextPolicy.NOT_APPLICABLE
    ),
    "tasks": PMWorkspaceIntent(
        "work", "tasks", "tasks", project_context_policy=ProjectContextPolicy.OPTIONAL
    ),
    "scheduling": PMWorkspaceIntent(
        "work", "scheduling", "planning", project_context_policy=ProjectContextPolicy.REQUIRED
    ),
    "resources": PMWorkspaceIntent(
        "workload", "resources", "resources", project_context_policy=ProjectContextPolicy.OPTIONAL
    ),
    "timesheets": PMWorkspaceIntent(
        "workload",
        "timesheets",
        "review_queue",
        project_context_policy=ProjectContextPolicy.OPTIONAL,
    ),
    "financials": PMWorkspaceIntent(
        "finance", "financials", project_context_policy=ProjectContextPolicy.REQUIRED
    ),
    "register": PMWorkspaceIntent(
        "governance", "register", "register", project_context_policy=ProjectContextPolicy.OPTIONAL
    ),
    "collaboration": PMWorkspaceIntent(
        "governance",
        "collaboration",
        "collaboration",
        project_context_policy=ProjectContextPolicy.OPTIONAL,
    ),
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
    "ProjectContextPolicy",
    "compatibility_route_intent",
    "workspace_intent",
]
