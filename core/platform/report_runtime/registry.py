from __future__ import annotations

from .contracts import ReportDefinition


class ReportDefinitionRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ReportDefinition] = {}

    @staticmethod
    def normalize_key(report_key: str) -> str:
        normalized = str(report_key or "").strip().lower()
        if not normalized:
            raise ValueError("Report key is required.")
        return normalized

    def register(self, definition: ReportDefinition) -> None:
        key = self.normalize_key(definition.report_key)
        if key in self._definitions:
            raise ValueError(f"Report definition is already registered for '{key}'.")
        self._definitions[key] = definition

    def has(self, report_key: str) -> bool:
        return self.normalize_key(report_key) in self._definitions

    def get(self, report_key: str) -> ReportDefinition:
        key = self.normalize_key(report_key)
        try:
            return self._definitions[key]
        except KeyError as exc:
            raise ValueError(f"Unsupported report type: {report_key}") from exc

    def list_report_keys(self) -> tuple[str, ...]:
        return tuple(self._definitions.keys())


__all__ = ["ReportDefinitionRegistry"]
