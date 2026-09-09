from __future__ import annotations

from src.core.platform.application.tenant.modules import ModuleGuardedServiceMixin


class ProjectManagementModuleGuardMixin(ModuleGuardedServiceMixin):
    _module_guard_code = "project_management"
    _module_guard_exempt_methods = frozenset({"consume_last_overallocation_warning"})

    @property
    def current_actor_user_id(self) -> str | None:
        """The authenticated actor's user_id, or None if there is no session --
        callers that require an actor should raise their own domain-specific error."""
        principal = getattr(getattr(self, "_user_session", None), "principal", None)
        return getattr(principal, "user_id", None)


__all__ = ["ProjectManagementModuleGuardMixin"]
