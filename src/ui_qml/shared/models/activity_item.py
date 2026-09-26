"""Canonical presentation shape for one row rendered by App.Widgets.ActivityFeed.

ActivityFeed is a renderer + interaction emitter only -- it never infers
meaning from display text. Every field here is presenter-owned: whichever
builder knows the domain (a generic Activity entry, an Audit entry projected
for a contextual preview, a comment digest, a scheduling insight, ...)
supplies title/description/tone/icon explicitly before handing the item to
this shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

VALID_TONES: frozenset[str] = frozenset({"neutral", "info", "success", "warning", "danger"})
_DEFAULT_TONE = "neutral"
_DEFAULT_ICON_KEY = "history"
_DEFAULT_ACTOR_DISPLAY = "System"

# Verb-based tone classification for an `entity.verb`-style action code.
_DANGER_ACTION_KEYWORDS = ("delet", "cancel", "reject", "close", "remov")
_WARNING_ACTION_KEYWORDS = ("updat", "edit", "modif", "submit", "post", "transfer", "issue", "return", "adjust")
_SUCCESS_ACTION_KEYWORDS = ("creat", "add", "open", "approv", "complet")

# Entity-type to App.Icons registry key. An unmapped entity type renders
# with the "history" fallback -- not every entity type needs a dedicated icon.
_ENTITY_ICON_KEYS: dict[str, str] = {
    "project": "project",
    "project_resource": "resources",
    "task": "tasks",
    "task_assignment": "tasks",
    "task_comment": "collaboration",
    "employee": "employee",
    "department": "department",
    "site": "site",
    "party": "party",
    "document": "documents",
    "document_structure": "documents",
    "organization": "organization",
    "register_entry": "register",
    "portfolio_intake_item": "portfolio",
    "portfolio_scenario": "portfolio",
    "portfolio_scoring_template": "portfolio",
    "portfolio_project_dependency": "portfolio",
    "resource": "resources",
    "resource_skill": "resources",
    "resource_certification": "resources",
    "module_entitlement": "module",
}


def tone_for_action(action: str) -> str:
    normalized = (action or "").lower()
    if any(keyword in normalized for keyword in _DANGER_ACTION_KEYWORDS):
        return "danger"
    if any(keyword in normalized for keyword in _WARNING_ACTION_KEYWORDS):
        return "warning"
    if any(keyword in normalized for keyword in _SUCCESS_ACTION_KEYWORDS):
        return "success"
    return "neutral"


def icon_key_for_entity_type(entity_type: str) -> str:
    return _ENTITY_ICON_KEYS.get((entity_type or "").strip().lower(), _DEFAULT_ICON_KEY)


def humanize_action(action: str) -> str:
    return (action or "").replace(".", " ").replace("_", " ").strip().title()


@dataclass(frozen=True)
class ActivityItemViewModel:
    id: str
    # Headline of WHAT happened -- never the actor. ("Project created", not "Ada".)
    title: str
    description: str = ""
    # Optional additional context, e.g. a field-level change summary.
    supporting_text: str = ""
    actor_display: str = _DEFAULT_ACTOR_DISPLAY
    # Raw machine-readable timestamp -- kept as a real datetime, not pre-formatted.
    occurred_at: datetime | None = None
    # Presenter-formatted display timestamp (whatever format fits the screen).
    occurred_at_label: str = ""
    # Domain-neutral App.Icons.AppIcon registry key.
    icon_key: str = _DEFAULT_ICON_KEY
    # Explicit semantic tone -- never derived from title/description/badgeLabel text.
    # Colors both the row's icon accent and its badge chip.
    tone: str = _DEFAULT_TONE
    # Optional related-object display value (e.g. a project/task name this event is about).
    subject_display: str = ""
    # Optional short badge -- a real state/outcome (Approved, Critical) or a stable
    # display category (Mention, Comment). Leave "" for an ordinary event with
    # neither, and ActivityFeed reserves no space for it.
    badge_label: str = ""
    # Optional opaque activation/navigation payload. ActivityFeed treats a non-None
    # value as "this row is clickable" and hands it back unmodified via itemActivated
    # -- it never interprets the contents. None/omitted means not independently
    # clickable (the feed's own `rowsActivatable` override still applies).
    activation_state: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.tone not in VALID_TONES:
            object.__setattr__(self, "tone", _DEFAULT_TONE)


def serialize_activity_item(item: ActivityItemViewModel) -> dict[str, Any]:
    """The one canonical camelCase shape App.Widgets.ActivityFeed reads."""
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "supportingText": item.supporting_text,
        "actorDisplay": item.actor_display,
        "occurredAt": item.occurred_at.isoformat() if item.occurred_at else None,
        "occurredAtLabel": item.occurred_at_label,
        "iconKey": item.icon_key,
        "tone": item.tone,
        "subjectDisplay": item.subject_display,
        "badgeLabel": item.badge_label,
        "activationState": item.activation_state,
    }


def serialize_activity_items(items: Any) -> list[dict[str, Any]]:
    return [serialize_activity_item(item) for item in items]


__all__ = [
    "VALID_TONES",
    "ActivityItemViewModel",
    "humanize_action",
    "icon_key_for_entity_type",
    "serialize_activity_item",
    "serialize_activity_items",
    "tone_for_action",
]
