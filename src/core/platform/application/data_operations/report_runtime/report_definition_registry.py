from __future__ import annotations

from src.core.platform.common.exceptions import (
    UnsupportedOperationError,
    ValidationError,
)
from src.core.platform.domain.data_operations.report_runtime.report_definition import (
    ReportDefinition,
)


class ReportDefinitionRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ReportDefinition] = {}

    @staticmethod
    def normalize_key(report_key: str) -> str:
        normalized = str(report_key or "").strip().lower()
        if not normalized:
            raise ValidationError("Report key is required.", code="REPORT_KEY_REQUIRED")
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
            raise UnsupportedOperationError(
                f"Unsupported report type: {report_key}", code="REPORT_TYPE_UNSUPPORTED"
            ) from exc

    def list_report_keys(self) -> tuple[str, ...]:
        return tuple(self._definitions.keys())


__all__ = ["ReportDefinitionRegistry"]
