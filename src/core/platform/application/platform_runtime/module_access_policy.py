from __future__ import annotations

# Single authoritative definition of which permission codes make an
# EnterpriseModule accessible to the current user. A module is accessible
# only if the user holds at least one permission whose dot-namespaced prefix
# is registered here for that module -- an unregistered module code is
# never accessible, matching the fail-closed posture used everywhere else
# in this codebase. Any consumer that needs to know "can this user use
# EnterpriseModule X" -- shell navigation, Global Overview module cards, or
# a future consumer -- must read this mapping rather than keeping its own
# copy.
#
# Platform is deliberately NOT registered here. It is not an
# EnterpriseModule (only project_management/qhse/hr_management are
# registered in the module catalog -- see DEFAULT_ENTERPRISE_MODULES) and
# must never be treated as one merely to support a Global Overview card.
# Platform's own accessibility is a core-application/permission concern,
# handled separately by whatever consumes it directly.
#
# Existing QML navigation (PlatformNavigation.qml) still carries its own
# inline destination->permission mapping and has not been converged onto
# this policy -- that convergence is a pending frontend step, not done here.
MODULE_PERMISSION_PREFIXES: dict[str, tuple[str, ...]] = {
    "project_management": (
        "task",
        "project",
        "timesheet",
        "resource",
        "portfolio",
        "financial",
        "project_cost",
        "baseline",
        "register",
    ),
    "inventory": ("inventory",),
}


def is_module_accessible(module_code: str, permissions: frozenset[str]) -> bool:
    prefixes = MODULE_PERMISSION_PREFIXES.get(module_code, ())
    if not prefixes:
        return False
    return any(permission.split(".", 1)[0] in prefixes for permission in permissions)


__all__ = ["MODULE_PERMISSION_PREFIXES", "is_module_accessible"]
