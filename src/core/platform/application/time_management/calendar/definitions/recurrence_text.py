"""Translation between a human-friendly recurrence editor state and the
RFC5545 RRULE string the domain/resolver actually execute.

RFC5545 RRULE + python-dateutil remain the canonical persistence/execution
format (see WorkingTimeCalculator.recurring_event_occurs_on) -- this module
only translates for display and for the visual recurrence editor; it never
changes how a recurrence rule is evaluated.

Editor state shape (the single source of truth the QML builder reads/writes):
    {
        "frequency": "DAILY" | "WEEKLY" | "EVERY_WEEKDAY" | "MONTHLY" | "YEARLY",
        "interval": int,                 # "every N days/weeks/months/years"
        "byDay": ["MO", "WE", ...],       # WEEKLY only
        "monthlyMode": "DAY_OF_MONTH" | "NTH_WEEKDAY",
        "dayOfMonth": int,                # MONTHLY + DAY_OF_MONTH
        "nth": int,                       # MONTHLY + NTH_WEEKDAY: 1-4, or -1 for "last"
        "nthWeekday": "MO" .. "SU",       # MONTHLY + NTH_WEEKDAY
    }

A rule that doesn't match any shape this module generates (hand-edited,
or using RRULE parts this editor doesn't expose, e.g. BYWEEKNO/UNTIL/COUNT)
parses to None -- the caller falls back to a read-only "Advanced" display of
the raw RRULE rather than guessing or silently dropping meaning.
"""

from __future__ import annotations

from datetime import date

_WEEKDAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
_WEEKDAY_NAMES = {
    "MO": "Monday", "TU": "Tuesday", "WE": "Wednesday", "TH": "Thursday",
    "FR": "Friday", "SA": "Saturday", "SU": "Sunday",
}
_WEEKDAY_ORDER = {code: i for i, code in enumerate(_WEEKDAY_CODES)}
_EVERY_WEEKDAY_SET = {"MO", "TU", "WE", "TH", "FR"}
_NTH_LABELS = {1: "first", 2: "second", 3: "third", 4: "fourth", -1: "last"}
_MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}

DEFAULT_EDITOR_STATE: dict[str, object] = {
    "frequency": "WEEKLY",
    "interval": 1,
    "byDay": [],
    "monthlyMode": "DAY_OF_MONTH",
    "dayOfMonth": 1,
    "nth": 1,
    "nthWeekday": "MO",
}


def _join_names(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def _sorted_days(codes: list[str]) -> list[str]:
    return sorted((c for c in codes if c in _WEEKDAY_ORDER), key=lambda c: _WEEKDAY_ORDER[c])


def build_rrule_from_editor_state(state: dict[str, object]) -> str:
    """Editor state -> RRULE. Never embeds UNTIL/COUNT -- "ends" is owned by
    the recurring event's own effective_from/effective_to fields, not the
    rule string, so there is exactly one authoritative end-date mapping."""
    frequency = str(state.get("frequency", "") or "").upper()
    interval = max(1, int(state.get("interval", 1) or 1))

    if frequency == "DAILY":
        parts = ["FREQ=DAILY"]
        if interval > 1:
            parts.append(f"INTERVAL={interval}")
        return ";".join(parts)

    if frequency == "EVERY_WEEKDAY":
        return "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"

    if frequency == "WEEKLY":
        days = _sorted_days([str(d).upper() for d in (state.get("byDay") or [])])
        if not days:
            raise ValueError("Weekly recurrence requires at least one selected day.")
        parts = ["FREQ=WEEKLY"]
        if interval > 1:
            parts.append(f"INTERVAL={interval}")
        parts.append("BYDAY=" + ",".join(days))
        return ";".join(parts)

    if frequency == "MONTHLY":
        parts = ["FREQ=MONTHLY"]
        if interval > 1:
            parts.append(f"INTERVAL={interval}")
        mode = str(state.get("monthlyMode", "DAY_OF_MONTH") or "DAY_OF_MONTH").upper()
        if mode == "NTH_WEEKDAY":
            nth = int(state.get("nth", 1) or 1)
            weekday = str(state.get("nthWeekday", "MO") or "MO").upper()
            parts.append(f"BYDAY={weekday}")
            parts.append(f"BYSETPOS={nth}")
        else:
            day_of_month = int(state.get("dayOfMonth", 1) or 1)
            parts.append(f"BYMONTHDAY={day_of_month}")
        return ";".join(parts)

    if frequency == "YEARLY":
        parts = ["FREQ=YEARLY"]
        if interval > 1:
            parts.append(f"INTERVAL={interval}")
        return ";".join(parts)

    raise ValueError(f"Unsupported recurrence frequency: {frequency!r}")


def _parse_rrule_parts(rrule: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for segment in str(rrule or "").split(";"):
        if "=" not in segment:
            continue
        key, _, value = segment.partition("=")
        parts[key.strip().upper()] = value.strip()
    return parts


_RECOGNIZED_KEYS = {"FREQ", "INTERVAL", "BYDAY", "BYMONTHDAY", "BYSETPOS"}


def parse_rrule_to_editor_state(rrule: str) -> dict[str, object] | None:
    """RRULE -> editor state, or None when the rule uses a shape this editor
    doesn't produce/understand (the caller must fall back to a read-only
    Advanced display rather than guessing)."""
    parts = _parse_rrule_parts(rrule)
    if not parts or "FREQ" not in parts:
        return None
    if any(key not in _RECOGNIZED_KEYS for key in parts):
        return None

    freq = parts["FREQ"].upper()
    try:
        interval = int(parts.get("INTERVAL", "1"))
    except ValueError:
        return None
    if interval < 1:
        return None

    if freq == "DAILY":
        if "BYDAY" in parts or "BYMONTHDAY" in parts or "BYSETPOS" in parts:
            return None
        return {**DEFAULT_EDITOR_STATE, "frequency": "DAILY", "interval": interval}

    if freq == "WEEKLY":
        if "BYMONTHDAY" in parts or "BYSETPOS" in parts or "BYDAY" not in parts:
            return None
        days = _sorted_days([d.strip().upper() for d in parts["BYDAY"].split(",") if d.strip()])
        if not days:
            return None
        if interval == 1 and set(days) == _EVERY_WEEKDAY_SET:
            return {**DEFAULT_EDITOR_STATE, "frequency": "EVERY_WEEKDAY", "interval": 1, "byDay": days}
        return {**DEFAULT_EDITOR_STATE, "frequency": "WEEKLY", "interval": interval, "byDay": days}

    if freq == "MONTHLY":
        has_day_of_month = "BYMONTHDAY" in parts
        has_nth_weekday = "BYDAY" in parts and "BYSETPOS" in parts
        if has_day_of_month and not has_nth_weekday:
            try:
                day_of_month = int(parts["BYMONTHDAY"])
            except ValueError:
                return None
            return {
                **DEFAULT_EDITOR_STATE, "frequency": "MONTHLY", "interval": interval,
                "monthlyMode": "DAY_OF_MONTH", "dayOfMonth": day_of_month,
            }
        if has_nth_weekday and not has_day_of_month:
            weekday = parts["BYDAY"].strip().upper()
            if weekday not in _WEEKDAY_NAMES:
                return None
            try:
                nth = int(parts["BYSETPOS"])
            except ValueError:
                return None
            if nth not in _NTH_LABELS:
                return None
            return {
                **DEFAULT_EDITOR_STATE, "frequency": "MONTHLY", "interval": interval,
                "monthlyMode": "NTH_WEEKDAY", "nth": nth, "nthWeekday": weekday,
            }
        return None

    if freq == "YEARLY":
        if "BYDAY" in parts or "BYMONTHDAY" in parts or "BYSETPOS" in parts:
            return None
        return {**DEFAULT_EDITOR_STATE, "frequency": "YEARLY", "interval": interval}

    return None


def humanize_rrule(rrule: str, *, effective_from: date | None = None) -> str:
    """Human-readable recurrence summary, generated from the actual RRULE --
    never maintained as independent business state. Falls back to the raw
    RRULE string for a shape this module doesn't recognize (Advanced/custom
    rules), so nothing is ever silently hidden."""
    state = parse_rrule_to_editor_state(rrule)
    if state is None:
        return str(rrule or "")

    frequency = state["frequency"]
    interval = int(state["interval"])

    if frequency == "DAILY":
        return "Daily" if interval == 1 else f"Every {interval} days"

    if frequency == "EVERY_WEEKDAY":
        return "Every weekday"

    if frequency == "WEEKLY":
        days = [_WEEKDAY_NAMES[d] for d in state["byDay"]]
        day_text = _join_names(days)
        if len(days) == 1 and interval == 1:
            return f"Every {day_text}"
        if interval == 1:
            return f"Weekly on {day_text}"
        return f"Every {interval} weeks on {day_text}"

    if frequency == "MONTHLY":
        if state["monthlyMode"] == "NTH_WEEKDAY":
            nth_label = _NTH_LABELS.get(int(state["nth"]), "first")
            weekday_name = _WEEKDAY_NAMES.get(str(state["nthWeekday"]), "Monday")
            if interval == 1:
                return f"Monthly on the {nth_label} {weekday_name}"
            return f"Every {interval} months on the {nth_label} {weekday_name}"
        day_of_month = int(state["dayOfMonth"])
        if interval == 1:
            return f"Monthly on day {day_of_month}"
        return f"Every {interval} months on day {day_of_month}"

    if frequency == "YEARLY":
        if effective_from is not None:
            on_date = f"{effective_from.day} {_MONTH_NAMES[effective_from.month]}"
        else:
            on_date = ""
        suffix = f" on {on_date}" if on_date else ""
        if interval == 1:
            return f"Every year{suffix}"
        return f"Every {interval} years{suffix}"

    return str(rrule or "")


__all__ = [
    "DEFAULT_EDITOR_STATE",
    "build_rrule_from_editor_state",
    "humanize_rrule",
    "parse_rrule_to_editor_state",
]
