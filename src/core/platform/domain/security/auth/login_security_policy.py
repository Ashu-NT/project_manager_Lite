from __future__ import annotations

import os


def login_lockout_threshold() -> int:
    raw = os.getenv("PM_AUTH_LOCKOUT_ATTEMPTS", "5").strip() or "5"
    try:
        return max(1, int(raw))
    except ValueError:
        return 5


def login_lockout_minutes() -> int:
    raw = os.getenv("PM_AUTH_LOCKOUT_MINUTES", "15").strip() or "15"
    try:
        return max(1, int(raw))
    except ValueError:
        return 15


def session_timeout_minutes() -> int:
    raw = os.getenv("PM_AUTH_SESSION_MINUTES", "480").strip() or "480"
    try:
        return max(5, int(raw))
    except ValueError:
        return 480


__all__ = [
    "login_lockout_minutes",
    "login_lockout_threshold",
    "session_timeout_minutes",
]
