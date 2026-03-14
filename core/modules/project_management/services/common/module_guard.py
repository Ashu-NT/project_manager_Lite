from __future__ import annotations

from core.platform.modules.guard import ModuleGuardedServiceMixin


class ProjectManagementModuleGuardMixin(ModuleGuardedServiceMixin):
    _module_guard_code = "project_management"
    _module_guard_exempt_methods = frozenset({"consume_last_overallocation_warning"})


__all__ = ["ProjectManagementModuleGuardMixin"]
