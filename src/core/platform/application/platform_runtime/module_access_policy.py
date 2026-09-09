from __future__ import annotations

# Single authoritative definition of which permission codes make a module
# accessible to the current user. A module is accessible only if the user
# holds at least one permission whose dot-namespaced prefix is registered
# here for that module -- an unregistered module code is never accessible,
# matching the fail-closed posture used everywhere else in this codebase.
# Any consumer that needs to know "can this user use module X" -- shell
# navigation, Global Overview module cards, or a future consumer -- must
# read this mapping rather than keeping its own copy.
#
# "platform" is not itself a toggleable EnterpriseModule (only
# project_management/qhse/hr_management are registered in the module
# catalog today) -- it is kept here so any future consumer checking
# Platform-specific accessibility by permission alone has a single place to
# look, not a second copy of this table.
MODULE_PERMISSION_PREFIXES: dict[str, tuple[str, ...]] = {
    "platform": (
        "audit",
        "activity",
        "auth",
        "security",
        "settings",
        "access",
        "employee",
        "site",
        "party",
        "document",
        "approval",
        "organization",
        "tenant",
        "user",
        "platform",
    ),
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
