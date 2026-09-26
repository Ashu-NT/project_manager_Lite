from __future__ import annotations

from collections.abc import Sequence
from typing import Any

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

    Builds the lookup from the full user and employee lists once per page
    load (bounded, no per-row query). At current data volumes this is
    cheaper than a page-scoped fetch; if user/employee counts grow large
    enough for that to change, this should resolve only the actor ids
    present on the current page rather than listing every user/employee.
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


def build_activity_records(
    entries: Sequence[Any],
    *,
    actor_lookup: dict[str, str],
    lookups: dict[str, dict[str, str]] | None = None,
    field_labels: dict[str, str],
    field_lookup: dict[str, str] | None = None,
    boolean_fields: frozenset[str] = frozenset(),
) -> tuple[ActivityItemViewModel, ...]:
    """Map one entity's paged activity rows (`id`/`occurred_at`/`actor_id`/
    `action`/`entity_type`/`summary`/`details`, as returned by a bounded,
    server-paged activity reader) into the canonical `ActivityItemViewModel`
    shape: a row's own `summary` becomes the headline unless it is just the
    raw action code, in which case it is humanized; actor name resolution
    and an action/entity-derived icon/tone are applied; and a diff-summary
    supporting line is built from the same `{field: {from, to}}` shape every
    `record_activity(..., details={"changes": ...})` call in this codebase
    already uses.
    """
    resolved_lookups = dict(lookups or {})
    resolved_lookups["user"] = actor_lookup
    records = []
    for entry in entries:
        title = (
            entry.summary
            if entry.summary and entry.summary != entry.action
            else humanize_action(entry.action)
        )
        records.append(
            ActivityItemViewModel(
                id=entry.id,
                title=title,
                actor_display=actor_lookup.get(entry.actor_id or "", "") or "System",
                supporting_text=format_changes_summary(
                    entry.details.get("changes"),
                    resolved_lookups,
                    field_labels=field_labels,
                    field_lookup=field_lookup,
                    boolean_fields=boolean_fields,
                ),
                occurred_at=entry.occurred_at,
                occurred_at_label=entry.occurred_at.strftime("%d %b %Y %H:%M") if entry.occurred_at else "",
                icon_key=icon_key_for_entity_type(entry.entity_type),
                tone=tone_for_action(entry.action),
                subject_display=entry.entity_type.replace("_", " ").title(),
            )
        )
    return tuple(records)


__all__ = [
    "build_activity_records",
    "build_actor_lookup",
    "build_id_lookup",
]
