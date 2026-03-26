from __future__ import annotations

from core.platform.auth.session import UserSessionContext
from core.platform.common.runtime_access import enforce_runtime_access
from core.platform.modules.contracts import SupportsModuleEntitlements

from .registry import ReportDefinitionRegistry


class ReportRuntime:
    def __init__(
        self,
        registry: ReportDefinitionRegistry,
        *,
        user_session: UserSessionContext | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
    ) -> None:
        self._registry = registry
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def render(
        self,
        report_key: str,
        request: object,
        *,
        user_session: UserSessionContext | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
    ) -> object:
        definition = self._registry.get(report_key)
        enforce_runtime_access(
            module_catalog_service=(
                module_catalog_service
                if module_catalog_service is not None
                else self._module_catalog_service
            ),
            user_session=user_session if user_session is not None else self._user_session,
            module_code=definition.module_code,
            permission_code=definition.permission_code,
            operation_label=f"render {self._humanize_key(definition.report_key)} report",
        )
        return definition.render(request)

    @staticmethod
    def _humanize_key(value: str) -> str:
        return str(value or "").strip().replace("_", " ") or "report"


__all__ = ["ReportRuntime"]
