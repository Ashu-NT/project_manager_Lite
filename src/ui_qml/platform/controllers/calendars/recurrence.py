"""QML-facing bridge to the recurrence editor <-> RRULE translation. The
translation logic itself lives in
src.core.platform.application.time_management.calendar.definitions.recurrence_text
-- this module only adapts its plain-Python calls to the QVariantMap shapes
QML sends/reads, so RRULE construction is never scattered across QML."""

from __future__ import annotations

from datetime import date

from src.core.platform.application.time_management.calendar.definitions.recurrence_text import (
    DEFAULT_EDITOR_STATE,
    build_rrule_from_editor_state,
    humanize_rrule,
    parse_rrule_to_editor_state,
)


def recurrence_summary(rrule: str, effective_from_iso: str = "") -> str:
    effective_from = None
    if effective_from_iso:
        try:
            effective_from = date.fromisoformat(effective_from_iso)
        except ValueError:
            effective_from = None
    return humanize_rrule(rrule, effective_from=effective_from)


def build_recurrence_rule(state: dict) -> dict[str, object]:
    try:
        rrule = build_rrule_from_editor_state(dict(state or {}))
        return {"ok": True, "rrule": rrule, "errorMessage": ""}
    except ValueError as exc:
        return {"ok": False, "rrule": "", "errorMessage": str(exc)}


def parse_recurrence_rule(rrule: str) -> dict[str, object]:
    """Editor state for Edit-mode loading, or {"ok": False} when the rule
    doesn't match a shape the visual builder understands -- the dialog must
    fall back to its read-only Advanced display rather than guess."""
    state = parse_rrule_to_editor_state(rrule)
    if state is None:
        return {"ok": False}
    return {"ok": True, **state}


def default_recurrence_editor_state() -> dict[str, object]:
    return dict(DEFAULT_EDITOR_STATE)


__all__ = [
    "build_recurrence_rule",
    "default_recurrence_editor_state",
    "parse_recurrence_rule",
    "recurrence_summary",
]
