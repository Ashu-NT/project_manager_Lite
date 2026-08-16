from __future__ import annotations


WORKSPACE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "organization": ("settings.manage",),
    "calendar": ("task.read",),
    "site": ("settings.manage", "site.read"),
    "department": ("settings.manage", "department.read"),
    "employee": ("employee.read",),
    "user": ("auth.manage", "auth.read", "access.manage", "security.manage"),
    "party": ("settings.manage", "party.read"),
    "document": ("settings.manage",),
    "document_structure": ("settings.manage",),
    "access": ("access.manage",),
    "control": ("approval.request", "approval.decide", "audit.read"),
    "settings": ("settings.manage",),
}


__all__ = ["WORKSPACE_PERMISSIONS"]
