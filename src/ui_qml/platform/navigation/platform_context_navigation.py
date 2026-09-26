"""Resolves Platform's Context Navigation Tree: which destinations the
current session may see, grouped and ordered. Filtering is based on held
permission codes; QML receives only the resulting tree, never permission
codes or raw destination metadata."""

from __future__ import annotations

from src.ui_qml.shell.context_navigation import (
    ContextNavigationGroupViewModel,
    ContextNavigationItemViewModel,
    ContextNavigationViewModel,
)

_ROOT_GROUP = ""
_ORGANIZATION_GROUP = "organization"
_IDENTITY_ACCESS_GROUP = "identity_access"
_DOCUMENTS_GROUP = "documents"
_CONTROL_GROUP = "control"
_ADMINISTRATION_GROUP = "administration"

_GROUP_LABELS: dict[str, str] = {
    _ROOT_GROUP: "",
    _ORGANIZATION_GROUP: "Organization",
    _IDENTITY_ACCESS_GROUP: "Identity & Access",
    _DOCUMENTS_GROUP: "Documents",
    _CONTROL_GROUP: "Control",
    _ADMINISTRATION_GROUP: "Administration",
}

_GROUP_ORDER: dict[str, int] = {
    _ROOT_GROUP: 0,
    _ORGANIZATION_GROUP: 10,
    _IDENTITY_ACCESS_GROUP: 20,
    _DOCUMENTS_GROUP: 30,
    _CONTROL_GROUP: 40,
    _ADMINISTRATION_GROUP: 50,
}

# (id, label, icon_key, group_id, order, required_permissions)
# `required_permissions` is an OR-of-any set, exactly matching the
# pre-migration QML policy this replaces -- never sent to QML.
_DESTINATIONS: tuple[tuple[str, str, str, str, int, tuple[str, ...]], ...] = (
    ("overview", "Overview", "dashboard", _ROOT_GROUP, 0, ()),
    ("organizations", "Organizations", "organization", _ORGANIZATION_GROUP, 0, ("settings.manage",)),
    ("sites", "Sites", "site", _ORGANIZATION_GROUP, 10, ("settings.manage", "site.read")),
    ("departments", "Departments", "department", _ORGANIZATION_GROUP, 20, ("settings.manage", "department.read")),
    ("employees", "Employees", "employee", _ORGANIZATION_GROUP, 30, ("employee.read",)),
    ("parties", "Parties", "party", _ORGANIZATION_GROUP, 40, ("settings.manage", "party.read")),
    ("calendars", "Calendars", "calendar", _ORGANIZATION_GROUP, 50, ("task.read",)),
    (
        "users",
        "Users",
        "user",
        _IDENTITY_ACCESS_GROUP,
        0,
        ("auth.manage", "auth.read", "access.manage", "security.manage"),
    ),
    ("access", "Roles & Access", "access", _IDENTITY_ACCESS_GROUP, 10, ("access.manage",)),
    ("documents", "Documents", "documents", _DOCUMENTS_GROUP, 0, ("settings.manage",)),
    ("structures", "Document Structures", "module", _DOCUMENTS_GROUP, 10, ("settings.manage",)),
    ("control_approvals", "Approvals", "approve", _CONTROL_GROUP, 0, ("approval.request", "approval.decide")),
    ("control_audit", "Audit", "audit", _CONTROL_GROUP, 10, ("audit.read",)),
    ("settings", "Settings", "settings", _ADMINISTRATION_GROUP, 0, ("settings.manage",)),
    ("tenants", "Tenant Management", "tenant", _ADMINISTRATION_GROUP, 10, ("platform.admin",)),
)


def _is_destination_visible(required_permissions: tuple[str, ...], *, held_permissions: frozenset[str]) -> bool:
    if not required_permissions:
        return True
    return any(permission in held_permissions for permission in required_permissions)


def build_platform_context_navigation(
    *, held_permissions: frozenset[str]
) -> ContextNavigationViewModel:
    """Resolve Platform's Context Navigation Tree for the given held
    permission codes."""
    visible = [
        destination
        for destination in _DESTINATIONS
        if _is_destination_visible(destination[5], held_permissions=held_permissions)
    ]

    groups: dict[str, list[ContextNavigationItemViewModel]] = {}
    for destination_id, label, icon_key, group_id, order, _permissions in visible:
        groups.setdefault(group_id, []).append(
            ContextNavigationItemViewModel(
                id=destination_id,
                label=label,
                icon_key=icon_key,
                route_id=destination_id,
                group_id=group_id,
                order=order,
            )
        )

    group_view_models = [
        ContextNavigationGroupViewModel(
            id=group_id,
            label=_GROUP_LABELS.get(group_id, group_id),
            order=_GROUP_ORDER.get(group_id, 999),
            items=tuple(sorted(items, key=lambda item: item.order)),
        )
        for group_id, items in groups.items()
    ]

    return ContextNavigationViewModel(
        workspace_id="platform",
        title="Platform",
        groups=tuple(group_view_models),
    )


__all__ = ["build_platform_context_navigation"]
