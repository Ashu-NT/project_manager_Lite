from __future__ import annotations

from .registry import ReportDefinitionRegistry


class ReportRuntime:
    def __init__(self, registry: ReportDefinitionRegistry) -> None:
        self._registry = registry

    def render(self, report_key: str, request: object) -> object:
        definition = self._registry.get(report_key)
        return definition.render(request)


__all__ = ["ReportRuntime"]
