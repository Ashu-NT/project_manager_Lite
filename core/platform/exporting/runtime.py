from __future__ import annotations

from core.platform.auth.session import UserSessionContext
from core.platform.common.runtime_access import enforce_runtime_access
from core.platform.modules.contracts import SupportsModuleEntitlements

from .delivery import finalize_artifact
from .models import ExportArtifact
from .registry import ExportDefinitionRegistry


class ExportRuntime:
    def __init__(
        self,
        registry: ExportDefinitionRegistry,
        *,
        user_session: UserSessionContext | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
    ) -> None:
        self._registry = registry
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def export(
        self,
        operation_key: str,
        request: object,
        *,
        user_session: UserSessionContext | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
    ) -> ExportArtifact:
        definition = self._registry.get(operation_key)
        enforce_runtime_access(
            module_catalog_service=(
                module_catalog_service
                if module_catalog_service is not None
                else self._module_catalog_service
            ),
            user_session=user_session if user_session is not None else self._user_session,
            module_code=definition.module_code,
            permission_code=definition.permission_code,
            operation_label=f"export {self._humanize_key(definition.operation_key)}",
        )
        return finalize_artifact(definition.export(request))

    @staticmethod
    def _humanize_key(value: str) -> str:
        return str(value or "").strip().replace("_", " ") or "artifact"


__all__ = ["ExportRuntime"]
