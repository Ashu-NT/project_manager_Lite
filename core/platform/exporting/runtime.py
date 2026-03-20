from __future__ import annotations

from .delivery import finalize_artifact
from .models import ExportArtifact
from .registry import ExportDefinitionRegistry


class ExportRuntime:
    def __init__(self, registry: ExportDefinitionRegistry) -> None:
        self._registry = registry

    def export(self, operation_key: str, request: object) -> ExportArtifact:
        definition = self._registry.get(operation_key)
        return finalize_artifact(definition.export(request))


__all__ = ["ExportRuntime"]
