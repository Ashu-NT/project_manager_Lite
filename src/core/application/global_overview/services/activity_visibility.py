from __future__ import annotations

_CORE_PLATFORM_MODULE = "platform"


def is_activity_visible(module: str, *, accessible_module_codes: frozenset[str]) -> bool:
    """Whether a Recent Activity entry's module value may be shown to the current user.

    Platform has no enable/license lifecycle (see module_access_policy.py), so its
    activity is gated only by ordinary Platform-area access, never by
    list_accessible_modules() -- there is no fake "platform" EnterpriseModule to check
    against. Every other module value is a real EnterpriseModule code and is visible
    only when it appears in the caller's already-computed accessible-module set. An
    unrecognized module value is hidden by default (fail closed), since the only
    activity currently ever recorded uses module="project_management" -- there is no
    verified generic/core classification for anything else yet.
    """
    normalized = str(module or "").strip().lower()
    if normalized == _CORE_PLATFORM_MODULE:
        return True
    return normalized in accessible_module_codes


__all__ = ["is_activity_visible"]
