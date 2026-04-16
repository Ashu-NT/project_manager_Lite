from __future__ import annotations

from pathlib import Path

from core.platform.auth.session import UserSessionContext
from core.platform.common.runtime_access import enforce_runtime_access
from core.platform.exporting import ExportArtifact, ExportArtifactDraft, finalize_artifact
from core.platform.modules.contracts import SupportsModuleEntitlements
from src.core.platform.runtime_tracking import RuntimeExecutionService

from src.core.platform.report_runtime.application.report_definition_registry import (
    ReportDefinitionRegistry,
)


class ReportRuntime:
    def __init__(
        self,
        registry: ReportDefinitionRegistry,
        *,
        user_session: UserSessionContext | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
        runtime_execution_service: RuntimeExecutionService | None = None,
    ) -> None:
        self._registry = registry
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._runtime_execution_service = runtime_execution_service

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
        execution = (
            self._runtime_execution_service.start_execution(
                operation_type="report",
                operation_key=definition.report_key,
                module_code=definition.module_code,
                output_path=getattr(request, "output_path", None),
            )
            if self._runtime_execution_service is not None
            else None
        )
        try:
            rendered = definition.render(request)
            if execution is not None:
                artifact = self._extract_artifact(rendered)
                self._runtime_execution_service.complete_execution(
                    execution,
                    output_path=getattr(artifact, "file_path", None) if artifact is not None else getattr(rendered, "file_path", None),
                    output_file_name=getattr(artifact, "file_name", None) if artifact is not None else None,
                    output_media_type=getattr(artifact, "media_type", None) if artifact is not None else None,
                    output_metadata=dict(getattr(artifact, "metadata", {}) or {}) if artifact is not None else None,
                )
            return rendered
        except Exception as exc:
            if execution is not None:
                self._runtime_execution_service.fail_execution(execution, error_message=str(exc))
            raise

    @staticmethod
    def _humanize_key(value: str) -> str:
        return str(value or "").strip().replace("_", " ") or "report"

    @staticmethod
    def _extract_artifact(rendered: object):
        if isinstance(rendered, (ExportArtifact, ExportArtifactDraft, str, Path)):
            return finalize_artifact(rendered)
        return None


__all__ = ["ReportRuntime"]
