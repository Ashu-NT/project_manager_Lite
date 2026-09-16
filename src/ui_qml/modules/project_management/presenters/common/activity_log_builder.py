from __future__ import annotations

from typing import Any, Sequence

from src.ui_qml.shared.models.activity_item import (
    ActivityItemViewModel,
    humanize_action,
    icon_key_for_entity_type,
    tone_for_action,
)

def build_id_lookup(list_result) -> dict[str, str]:
    if not list_result.ok or list_result.data is None:
        return {}
    return {str(row.id): str(getattr(row, "name", "") or "") for row in list_result.data}


def build_user_lookup(list_result) -> dict[str, str]:
    if not list_result.ok or list_result.data is None:
        return {}
    return {
        str(row.id): str(row.display_name or row.username)
        for row in list_result.data
    }


def build_actor_lookup(user_result, employee_result) -> dict[str, str]:
    """user_id -> display name, preferring the linked Employee's full name.

    Most users in this app are employees (`Employee.user_id` links back to
    the account), and an employee record's `full_name` is a real recorded
    name rather than a login-oriented username/display_name -- so an
    Employee match, when one exists, wins over the User account's own
    fields.
    """
    lookup = build_user_lookup(user_result)
    if employee_result is not None and employee_result.ok and employee_result.data is not None:
        for employee in employee_result.data:
            user_id = getattr(employee, "user_id", None)
            full_name = str(getattr(employee, "full_name", "") or "")
            if user_id and full_name:
                lookup[str(user_id)] = full_name
    return lookup


def resolve_change_value(
    field_name: str,
    raw_value: str | None,
    lookups: dict[str, dict[str, str]],
    *,
    boolean_fields: frozenset[str] = frozenset(),
    field_lookup: dict[str, str] | None = None,
) -> str:
    if raw_value is None:
        return "-"
    if field_name in boolean_fields:
        return "Active" if raw_value == "True" else "Inactive"
    lookup_key = (field_lookup or {}).get(field_name)
    if lookup_key is not None:
        resolved = lookups.get(lookup_key, {}).get(raw_value)
        if resolved:
            return resolved
    if field_name == "status":
        return raw_value.replace("_", " ").title()
    return raw_value


def format_changes_summary(
    changes: object,
    lookups: dict[str, dict[str, str]],
    *,
    field_labels: dict[str, str],
    field_lookup: dict[str, str] | None = None,
    boolean_fields: frozenset[str] = frozenset(),
) -> str:
    if not isinstance(changes, dict) or not changes:
        return ""
    parts: list[str] = []
    for field_name, label in field_labels.items():
        change = changes.get(field_name)
        if not isinstance(change, dict):
            continue
        from_text = resolve_change_value(
            field_name, change.get("from"), lookups,
            boolean_fields=boolean_fields, field_lookup=field_lookup,
        )
        to_text = resolve_change_value(
            field_name, change.get("to"), lookups,
            boolean_fields=boolean_fields, field_lookup=field_lookup,
        )
        parts.append(f"{label}: {from_text} → {to_text}")
    return "; ".join(parts)


def fetch_entity_activity_entries(
    activity_api,
    *,
    entity_type: str,
    entity_id: str,
    child_specs: Sequence[tuple[str, str]] = (),
    limit: int = 50,
) -> tuple[Any, ...]:
    """Fetch and merge activity for one primary entity plus any child entity
    types, sorted newest first and capped at `limit`.

    `child_specs` is a sequence of `(child_entity_type, parent_entity_id)`
    pairs, queried via `parent_entity_id` (a real, indexed column on the
    activity record) -- e.g. a task's assignments record their own
    `task_assignment` activity with `parent_entity_id=<task_id>`. This is a
    tighter scope than `workspace_id`, which is shared by *every* entity
    type recorded against the same workspace and would silently pull in
    unrelated activity (e.g. a project's tasks and its resources both use
    `workspace_id=<project_id>`).

    Each separate query is deliberate, not a workaround: merging via one
    broad filter (workspace_id or otherwise) would expand a feed meant for
    "this entity and its direct children" into "everything that happens to
    share this workspace," which is a real scope violation, not a
    convenience.
    """
    if activity_api is None or not entity_id:
        return ()
    primary_result = activity_api.list_recent(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    all_entries = list(primary_result.data or ())
    any_ok = primary_result.ok
    for child_entity_type, parent_entity_id in child_specs:
        if not parent_entity_id:
            continue
        child_result = activity_api.list_recent(
            entity_type=child_entity_type,
            parent_entity_id=parent_entity_id,
            limit=limit,
        )
        any_ok = any_ok or child_result.ok
        all_entries.extend(child_result.data or ())
    if not any_ok:
        return ()
    return tuple(sorted(all_entries, key=lambda e: e.timestamp, reverse=True)[:limit])


def build_activity_records(
    entries: Sequence[Any],
    *,
    actor_lookup: dict[str, str],
    lookups: dict[str, dict[str, str]] | None = None,
    field_labels: dict[str, str],
    field_lookup: dict[str, str] | None = None,
    boolean_fields: frozenset[str] = frozenset(),
) -> tuple[ActivityItemViewModel, ...]:
    """Map raw `ActivityEntry` rows into the canonical `ActivityItemViewModel`
    shape: an entry's own `human_message` (or a humanized fallback of its
    action code) becomes the headline, actor name resolution and an
    action/entity-derived icon/tone are applied, and a diff-summary
    supporting line is built from the same `{field: {from, to}}` shape every
    `record_activity(..., details={"changes": ...})` call in this codebase
    already uses.
    """
    resolved_lookups = dict(lookups or {})
    resolved_lookups["user"] = actor_lookup
    records = []
    for entry in entries:
        records.append(
            ActivityItemViewModel(
                id=entry.id,
                title=entry.human_message or humanize_action(entry.action),
                actor_display=actor_lookup.get(entry.actor_id or "", "") or "System",
                supporting_text=format_changes_summary(
                    entry.details.get("changes"),
                    resolved_lookups,
                    field_labels=field_labels,
                    field_lookup=field_lookup,
                    boolean_fields=boolean_fields,
                ),
                occurred_at=entry.timestamp,
                occurred_at_label=entry.timestamp.strftime("%d %b %Y %H:%M") if entry.timestamp else "",
                icon_key=icon_key_for_entity_type(entry.entity_type),
                tone=tone_for_action(entry.action),
            )
        )
    return tuple(records)


__all__ = [
    "build_activity_records",
    "build_actor_lookup",
    "build_id_lookup",
    "build_user_lookup",
    "fetch_entity_activity_entries",
    "format_changes_summary",
    "humanize_action",
    "icon_key_for_entity_type",
    "resolve_change_value",
    "tone_for_action",
]
