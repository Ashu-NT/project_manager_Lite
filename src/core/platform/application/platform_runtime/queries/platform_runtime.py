from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.application.platform_runtime.dto import ModuleRuntimeSnapshot
from src.core.platform.application.platform_runtime.module_access_policy import (
    is_module_accessible,
)
from src.core.platform.application.platform_runtime.module_snapshot import (
    build_module_runtime_snapshot,
)
from src.core.platform.application.tenant.modules import ModuleCatalogQueryHandler
from src.core.platform.domain.security.auth.session import UserSessionContext


@dataclass(frozen=True)
class PlatformRuntimeContextSnapshot:
    context_label: str
    module_snapshot: ModuleRuntimeSnapshot


class PlatformRuntimeQueryHandler:
    """Assemble runtime snapshots and session-aware module accessibility."""

    def __init__(
        self,
        *,
        module_catalog_service: ModuleCatalogQueryHandler,
        user_session: UserSessionContext | None = None,
    ) -> None:
        self._module_catalog_service = module_catalog_service
        self._user_session = user_session

    def get_current_permissions(self) -> frozenset[str]:
        if self._user_session is None or self._user_session.principal is None:
            return frozenset()
        return frozenset(self._user_session.principal.permissions)

    def list_accessible_modules(self):
        permissions = self.get_current_permissions()
        return tuple(
            module
            for module in self._module_catalog_service.list_enabled_modules()
            if is_module_accessible(module.code, permissions)
        )

    def snapshot(self) -> PlatformRuntimeContextSnapshot:
        module_snapshot = build_module_runtime_snapshot(self._module_catalog_service)
        return PlatformRuntimeContextSnapshot(
            context_label=module_snapshot.context_label,
            module_snapshot=module_snapshot,
        )
